"""微信公众号 API 封装"""

import time
import httpx


WECHAT_BASE = "https://api.weixin.qq.com"


class WeChatAPIError(Exception):
    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"[{errcode}] {errmsg}")


class WeChatClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_expires_at: float = 0

    # ── Access Token ──────────────────────────────────────────────────────────

    def get_access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token

        resp = httpx.get(
            f"{WECHAT_BASE}/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            },
        )
        data = resp.json()
        self._check(data)
        self._token = data["access_token"]
        # 提前 60 秒刷新，避免边界问题
        self._token_expires_at = time.time() + data["expires_in"] - 60
        return self._token

    # ── 素材 ─────────────────────────────────────────────────────────────────

    def upload_thumb(self, image_path: str) -> str:
        """上传缩略图素材，返回 media_id"""
        token = self.get_access_token()
        with open(image_path, "rb") as f:
            resp = httpx.post(
                f"{WECHAT_BASE}/cgi-bin/material/add_material",
                params={"access_token": token, "type": "thumb"},
                files={"media": f},
            )
        data = resp.json()
        self._check(data)
        return data["media_id"]

    # ── 草稿 ─────────────────────────────────────────────────────────────────

    def add_draft(self, articles: list[dict]) -> str:
        """
        创建草稿，返回 media_id。
        articles 每项字段：title, author, digest, content,
                          content_source_url, thumb_media_id, need_open_comment
        """
        token = self.get_access_token()
        resp = httpx.post(
            f"{WECHAT_BASE}/cgi-bin/draft/add",
            params={"access_token": token},
            json={"articles": articles},
        )
        data = resp.json()
        self._check(data)
        return data["media_id"]

    def get_draft(self, media_id: str) -> dict:
        token = self.get_access_token()
        resp = httpx.post(
            f"{WECHAT_BASE}/cgi-bin/draft/get",
            params={"access_token": token},
            json={"media_id": media_id},
        )
        data = resp.json()
        self._check(data)
        return data

    # ── 发布 ─────────────────────────────────────────────────────────────────

    def publish(self, media_id: str) -> str:
        """提交发布，返回 publish_id"""
        token = self.get_access_token()
        resp = httpx.post(
            f"{WECHAT_BASE}/cgi-bin/freepublish/submit",
            params={"access_token": token},
            json={"media_id": media_id},
        )
        data = resp.json()
        self._check(data)
        return data["publish_id"]

    def get_publish_status(self, publish_id: str) -> dict:
        token = self.get_access_token()
        resp = httpx.post(
            f"{WECHAT_BASE}/cgi-bin/freepublish/get",
            params={"access_token": token},
            json={"publish_id": publish_id},
        )
        data = resp.json()
        self._check(data)
        return data

    # ── 内部工具 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _check(data: dict) -> None:
        if "errcode" in data and data["errcode"] != 0:
            raise WeChatAPIError(data["errcode"], data.get("errmsg", ""))
