from collections import defaultdict
from datetime import datetime, timezone

import requests


class FacebookServiceError(RuntimeError):
    pass


class FacebookService:
    def __init__(self, account, api_version="v19.0", timeout=15):
        self.account = account
        self.api_version = api_version
        self.timeout = timeout
        self.base_url = f"https://graph.facebook.com/{api_version}"

    def _get(self, path, params=None):
        query = dict(params or {})
        query["access_token"] = self.account.get_access_token()
        try:
            response = requests.get(
                f"{self.base_url}/{path.lstrip('/')}",
                params=query,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            detail = "Facebook API request failed"
            if getattr(exc, "response", None) is not None:
                try:
                    detail = exc.response.json().get("error", {}).get("message", detail)
                except ValueError:
                    pass
            raise FacebookServiceError(detail) from exc
        if "error" in payload:
            raise FacebookServiceError(payload["error"].get("message", "Facebook API error"))
        return payload

    @staticmethod
    def _insight_value(insights, metric):
        for item in insights.get("data", []):
            if item.get("name") == metric:
                values = item.get("values", [])
                return values[0].get("value", 0) if values else 0
        return 0

    def get_post_metrics(self, limit=50):
        fields = (
            "id,message,created_time,permalink_url,"
            "insights.metric(post_impressions,post_engaged_users,"
            "post_reactions_by_type_total)"
        )
        payload = self._get(
            f"{self.account.platform_user_id}/posts",
            {"fields": fields, "limit": min(limit, 100)},
        )
        posts = []
        pages = 0
        while payload and len(posts) < limit and pages < 5:
            for post in payload.get("data", []):
                insights = post.get("insights", {})
                reactions = self._insight_value(
                    insights, "post_reactions_by_type_total"
                )
                reaction_count = (
                    sum(value for value in reactions.values() if isinstance(value, int))
                    if isinstance(reactions, dict)
                    else int(reactions or 0)
                )
                engaged = int(
                    self._insight_value(insights, "post_engaged_users") or 0
                )
                posts.append(
                    {
                        "id": post["id"],
                        "title": (post.get("message") or "Facebook post")[:80],
                        "created_at": post.get("created_time"),
                        "url": post.get("permalink_url"),
                        "views": int(
                            self._insight_value(insights, "post_impressions") or 0
                        ),
                        "engagement": engaged,
                        "likes": reaction_count,
                        "shares": 0,
                        "average_watch_time": 0,
                    }
                )
                if len(posts) >= limit:
                    break
            next_url = payload.get("paging", {}).get("next")
            if not next_url or len(posts) >= limit:
                break
            try:
                response = requests.get(next_url, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise FacebookServiceError("Facebook pagination failed") from exc
            pages += 1
        return posts

    def get_normalized_stats(self):
        posts = self.get_post_metrics()
        daily = defaultdict(lambda: {"views": 0, "engagement": 0})
        for post in posts:
            date_key = self._date_key(post.get("created_at"))
            daily[date_key]["views"] += post["views"]
            daily[date_key]["engagement"] += post["engagement"]
        return {
            "platform": "facebook",
            "summary": {
                "views": sum(item["views"] for item in posts),
                "engagement": sum(item["engagement"] for item in posts),
                "content_count": len(posts),
            },
            "daily": [
                {"date": date, **values} for date, values in sorted(daily.items())
            ],
            "content": posts,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _date_key(value):
        if not value:
            return datetime.now(timezone.utc).date().isoformat()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return value[:10]

