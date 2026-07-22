import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode

import requests
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config import Config, ProductionConfig
from database import db
from models import SocialAccount, User
from services.facebook_service import FacebookService, FacebookServiceError
from services.tiktok_service import TikTokService, TikTokServiceError


LOGGER = logging.getLogger(__name__)


def create_app(config_object=None):
    app = Flask(__name__)
    environment = os.getenv("FLASK_ENV", "development")
    selected_config = config_object or (
        ProductionConfig if environment == "production" else Config
    )
    app.config.from_object(selected_config)
    if selected_config is ProductionConfig:
        ProductionConfig.validate()

    db.init_app(app)
    register_routes(app)
    register_error_handlers(app)

    @app.cli.command("init-db")
    def init_db():
        """Create database tables (use migrations for later schema changes)."""
        db.create_all()
        print("Database tables created.")

    return app


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validate_csrf():
    provided = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("csrf_token", "")
    if not expected or not hmac.compare_digest(provided, expected):
        abort(400, description="Invalid CSRF token")


def register_routes(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user():
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            validate_csrf()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                flash("Invalid email or password.", "error")
                return render_template("login.html"), 401
            session.clear()
            session["user_id"] = user.id
            session.permanent = True
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.post("/register")
    def register():
        validate_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if "@" not in email or len(email) > 255:
            flash("Enter a valid email address.", "error")
            return redirect(url_for("login"))
        if len(password) < 10:
            flash("Password must be at least 10 characters.", "error")
            return redirect(url_for("login"))
        user = User(email=email)
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account with that email already exists.", "error")
            return redirect(url_for("login"))
        session.clear()
        session["user_id"] = user.id
        session.permanent = True
        return redirect(url_for("dashboard"))

    @app.post("/logout")
    @login_required
    def logout():
        validate_csrf()
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def dashboard():
        user = current_user()
        connections = {account.platform: account for account in user.social_accounts}
        return render_template(
            "dashboard.html", user=user, connections=connections
        )

    @app.get("/auth/facebook")
    @login_required
    def facebook_auth():
        require_oauth_config("Facebook", "FACEBOOK_CLIENT_ID", "FACEBOOK_CLIENT_SECRET")
        state = secrets.token_urlsafe(32)
        session["facebook_oauth_state"] = state
        query = urlencode(
            {
                "client_id": app.config["FACEBOOK_CLIENT_ID"],
                "redirect_uri": app.config["FACEBOOK_REDIRECT_URI"],
                "state": state,
                "response_type": "code",
                "scope": "pages_show_list,pages_read_engagement,read_insights",
            }
        )
        return redirect(
            f"https://www.facebook.com/{app.config['FACEBOOK_API_VERSION']}/dialog/oauth?{query}"
        )

    @app.get("/auth/facebook/callback")
    @login_required
    def facebook_callback():
        validate_oauth_callback("facebook")
        if request.args.get("error"):
            flash("Facebook authorization was cancelled.", "error")
            return redirect(url_for("dashboard"))
        code = request.args.get("code")
        if not code:
            abort(400, description="Facebook did not return an authorization code")
        try:
            token_data = external_get_json(
                f"https://graph.facebook.com/{app.config['FACEBOOK_API_VERSION']}/oauth/access_token",
                {
                    "client_id": app.config["FACEBOOK_CLIENT_ID"],
                    "client_secret": app.config["FACEBOOK_CLIENT_SECRET"],
                    "redirect_uri": app.config["FACEBOOK_REDIRECT_URI"],
                    "code": code,
                },
            )
            user_token = token_data["access_token"]
            long_lived = external_get_json(
                f"https://graph.facebook.com/{app.config['FACEBOOK_API_VERSION']}/oauth/access_token",
                {
                    "grant_type": "fb_exchange_token",
                    "client_id": app.config["FACEBOOK_CLIENT_ID"],
                    "client_secret": app.config["FACEBOOK_CLIENT_SECRET"],
                    "fb_exchange_token": user_token,
                },
            )
            user_token = long_lived.get("access_token", user_token)
            pages = external_get_json(
                f"https://graph.facebook.com/{app.config['FACEBOOK_API_VERSION']}/me/accounts",
                {"access_token": user_token, "fields": "id,name,access_token"},
            ).get("data", [])
            if not pages:
                raise RuntimeError("No Facebook Page is available for this account")
            page = pages[0]
            expires_in = long_lived.get("expires_in") or token_data.get("expires_in")
            save_social_account(
                current_user(),
                "facebook",
                page["id"],
                page["access_token"],
                expires_in=int(expires_in) if expires_in else None,
            )
            flash(f"Connected Facebook Page: {page.get('name', page['id'])}.", "success")
        except (requests.RequestException, KeyError, RuntimeError, ValueError) as exc:
            LOGGER.exception("Facebook OAuth callback failed")
            flash(str(exc) or "Unable to connect Facebook.", "error")
        return redirect(url_for("dashboard"))

    @app.get("/auth/tiktok")
    @login_required
    def tiktok_auth():
        require_oauth_config("TikTok", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET")
        state = secrets.token_urlsafe(32)
        session["tiktok_oauth_state"] = state
        query = urlencode(
            {
                "client_key": app.config["TIKTOK_CLIENT_KEY"],
                "redirect_uri": app.config["TIKTOK_REDIRECT_URI"],
                "response_type": "code",
                "scope": "user.info.basic,video.list",
                "state": state,
            }
        )
        return redirect(f"https://www.tiktok.com/v2/auth/authorize/?{query}")

    @app.get("/auth/tiktok/callback")
    @login_required
    def tiktok_callback():
        validate_oauth_callback("tiktok")
        if request.args.get("error"):
            flash("TikTok authorization was cancelled.", "error")
            return redirect(url_for("dashboard"))
        code = request.args.get("code")
        if not code:
            abort(400, description="TikTok did not return an authorization code")
        try:
            response = requests.post(
                TikTokService.TOKEN_URL,
                data={
                    "client_key": app.config["TIKTOK_CLIENT_KEY"],
                    "client_secret": app.config["TIKTOK_CLIENT_SECRET"],
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": app.config["TIKTOK_REDIRECT_URI"],
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(
                    payload.get("error_description") or payload["error"]
                )
            save_social_account(
                current_user(),
                "tiktok",
                payload["open_id"],
                payload["access_token"],
                refresh_token=payload.get("refresh_token"),
                expires_in=int(payload.get("expires_in", 86400)),
            )
            flash("TikTok account connected.", "success")
        except (requests.RequestException, KeyError, RuntimeError, ValueError) as exc:
            LOGGER.exception("TikTok OAuth callback failed")
            flash(str(exc) or "Unable to connect TikTok.", "error")
        return redirect(url_for("dashboard"))

    @app.post("/auth/<platform>/disconnect")
    @login_required
    def disconnect(platform):
        validate_csrf()
        if platform not in {"facebook", "tiktok"}:
            abort(404)
        account = SocialAccount.query.filter_by(
            user_id=session["user_id"], platform=platform
        ).first_or_404()
        db.session.delete(account)
        db.session.commit()
        flash(f"Disconnected {platform.title()}.", "success")
        return redirect(url_for("dashboard"))

    @app.get("/api/v1/stats/facebook")
    @login_required
    def facebook_stats():
        account = get_social_account("facebook")
        if not account:
            return jsonify({"error": "Facebook is not connected", "platform": "facebook"}), 404
        try:
            return jsonify(
                FacebookService(
                    account, api_version=app.config["FACEBOOK_API_VERSION"]
                ).get_normalized_stats()
            )
        except FacebookServiceError as exc:
            LOGGER.warning("Facebook stats failed: %s", exc)
            return jsonify({"error": str(exc), "platform": "facebook"}), 502

    @app.get("/api/v1/stats/tiktok")
    @login_required
    def tiktok_stats():
        account = get_social_account("tiktok")
        if not account:
            return jsonify({"error": "TikTok is not connected", "platform": "tiktok"}), 404
        try:
            return jsonify(TikTokService(account).get_normalized_stats())
        except TikTokServiceError as exc:
            LOGGER.warning("TikTok stats failed: %s", exc)
            return jsonify({"error": str(exc), "platform": "tiktok"}), 502


def save_social_account(
    user, platform, platform_user_id, access_token, refresh_token=None, expires_in=None
):
    account = SocialAccount.query.filter_by(
        user_id=user.id, platform=platform
    ).first()
    if not account:
        account = SocialAccount(
            user_id=user.id,
            platform=platform,
            platform_user_id=platform_user_id,
            access_token="pending",
        )
        db.session.add(account)
    account.platform_user_id = platform_user_id
    account.set_access_token(access_token)
    if refresh_token:
        account.set_refresh_token(refresh_token)
    account.expires_at = (
        datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    )
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise RuntimeError("Unable to save the connected account")


def get_social_account(platform):
    return SocialAccount.query.filter_by(
        user_id=session["user_id"], platform=platform
    ).first()


def validate_oauth_callback(platform):
    expected = session.pop(f"{platform}_oauth_state", "")
    provided = request.args.get("state", "")
    if not expected or not hmac.compare_digest(expected, provided):
        abort(400, description="Invalid OAuth state")


def require_oauth_config(provider, *keys):
    if any(not current_app_config(key) for key in keys):
        abort(503, description=f"{provider} OAuth is not configured")


def current_app_config(key):
    from flask import current_app

    return current_app.config.get(key)


def external_get_json(url, params):
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"].get("message", "Provider API error"))
    return payload


def register_error_handlers(app):
    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(503)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": error.description}), error.code
        flash(error.description, "error")
        return redirect(url_for("dashboard") if current_user() else url_for("login"))

    @app.errorhandler(500)
    def handle_server_error(error):
        db.session.rollback()
        LOGGER.exception("Unhandled server error: %s", error)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return render_template("login.html"), 500


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
