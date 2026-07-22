from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

from database import db


class TikTokServiceError(RuntimeError):
    pass


class TikTokService:
    API_BASE = "https://open.tiktokapis.com/v2"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

    def __init__(self, account, timeout=15):
        self.account = account
        self.timeout = timeout

    def _ensure_access_token(self):
        now = datetime.utcnow()
        if self.account.expires_at and self.account.expires_at <= now + timedelta(minutes=5):
            self.refresh_access_token()
        return self.account.get_access_token()

    def refresh_access_token(self):
        refresh_token = self.account.get_refresh_token()
        if not refresh_token:
            raise TikTokServiceError("TikTok authorization expired; reconnect the account")
        try:
            response = requests.post(
                self.TOKEN_URL,
                data={
                    "client_key": current_app.config["TIKTOK_CLIENT_KEY"],
                    "client_secret": current_app.config["TIKTOK_CLIENT_SECRET"],
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise TikTokServiceError("Unable to refresh TikTok access token") from exc

        if payload.get("error"):
            message = payload.get("error_description") or payload.get("error")
            raise TikTokServiceError(message)
        self.account.set_access_token(payload["access_token"])
        if payload.get("refresh_token"):
            self.account.set_refresh_token(payload["refresh_token"])
        self.account.expires_at = datetime.utcnow() + timedelta(
            seconds=int(payload.get("expires_in", 86400))
        )
        db.session.commit()
        return payload["access_token"]

    def _post(self, path, payload, params=None):
        headers = {
            "Authorization": f"Bearer {self._ensure_access_token()}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                f"{self.API_BASE}/{path.lstrip('/')}",
                headers=headers,
                params=params,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            detail = "TikTok API request failed"
            if getattr(exc, "response", None) is not None:
                try:
                    detail = exc.response.json().get("error", {}).get("message", detail)
                except ValueError:
                    pass
            raise TikTokServiceError(detail) from exc
        error = data.get("error", {})
        if error and error.get("code", "ok") != "ok":
            raise TikTokServiceError(error.get("message", "TikTok API error"))
        return data.get("data", {})

    def get_video_metrics(self, limit=50):
        fields = (
            "id,title,create_time,share_url,view_count,like_count,"
            "comment_count,share_count,average_time_watched"
        )
        videos = []
        cursor = None
        pages = 0
        while len(videos) < limit and pages < 5:
            body = {"max_count": min(20, limit - len(videos))}
            if cursor is not None:
                body["cursor"] = cursor
            data = self._post("video/list/", body, {"fields": fields})
            for video in data.get("videos", []):
                likes = int(video.get("like_count", 0))
                shares = int(video.get("share_count", 0))
                comments = int(video.get("comment_count", 0))
                created = datetime.fromtimestamp(
                    int(video.get("create_time", 0)), tz=timezone.utc
                ).isoformat()
                videos.append(
                    {
                        "id": video["id"],
                        "title": (video.get("title") or "TikTok video")[:80],
                        "created_at": created,
                        "url": video.get("share_url"),
                        "views": int(video.get("view_count", 0)),
                        "engagement": likes + shares + comments,
                        "likes": likes,
                        "shares": shares,
                        "average_watch_time": float(
                            video.get("average_time_watched", 0) or 0
                        ),
                    }
                )
            if not data.get("has_more"):
                break
            cursor = data.get("cursor")
            pages += 1
        return videos

    def get_normalized_stats(self):
        videos = self.get_video_metrics()
        daily = defaultdict(lambda: {"views": 0, "engagement": 0})
        for video in videos:
            date_key = video["created_at"][:10]
            daily[date_key]["views"] += video["views"]
            daily[date_key]["engagement"] += video["engagement"]
        return {
            "platform": "tiktok",
            "summary": {
                "views": sum(item["views"] for item in videos),
                "engagement": sum(item["engagement"] for item in videos),
                "content_count": len(videos),
            },
            "daily": [
                {"date": date, **values} for date, values in sorted(daily.items())
            ],
            "content": videos,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
