"""
트윗 큐레이터

시뮬레이션 DB에서 일자별 액션을 읽어서
하루 5개 트윗을 선별하고 타임라인 형태로 반환한다.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional


# 액션별 우선순위 (높을수록 선별 우선)
ACTION_PRIORITY = {
    "create_post": 3,
    "quote_post": 2,
    "create_comment": 2,
    "repost": 1,
    "like_post": 0,
    "dislike_post": 0,
    "follow": 0,
    "do_nothing": -1,
}


def get_timeline(
    db_path: str,
    day: int,
    tweets_per_day: int = 5,
    minutes_per_round: int = 60,
) -> Dict[str, Any]:
    """
    특정 일차의 큐레이션된 타임라인을 반환.

    Args:
        db_path: twitter_simulation.db 경로
        day: 일차 (1~7)
        tweets_per_day: 하루에 보여줄 트윗 수
        minutes_per_round: 라운드당 시뮬 분

    Returns:
        {"day": int, "tweets": [...]}
    """
    rounds_per_day = (24 * 60) // minutes_per_round  # 24 rounds for 60min/round
    start_round = (day - 1) * rounds_per_day
    end_round = day * rounds_per_day

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # trace 테이블에서 해당 일차 액션들을 가져옴
    # OASIS trace schema: id, user_id, action, info, created_at
    rows = cursor.execute(
        """
        SELECT id, user_id, action, info, created_at
        FROM trace
        WHERE id > 0
        ORDER BY id ASC
        """
    ).fetchall()
    conn.close()

    if not rows:
        return {"day": day, "tweets": []}

    # 라운드 기반이 아니라 순서 기반으로 일자 분할
    # 전체 액션을 균등하게 7일로 나눔
    total_actions = len(rows)
    actions_per_day = max(total_actions // 7, 1)
    day_start = (day - 1) * actions_per_day
    day_end = day * actions_per_day if day < 7 else total_actions

    day_rows = rows[day_start:day_end]

    # 우선순위로 정렬하여 상위 N개 선별
    scored = []
    for row in day_rows:
        action = row["action"].lower() if row["action"] else ""
        priority = ACTION_PRIORITY.get(action, -1)
        if priority < 0:
            continue

        info = {}
        if row["info"]:
            try:
                info = json.loads(row["info"])
            except (json.JSONDecodeError, TypeError):
                info = {"raw": row["info"]}

        scored.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "action": row["action"],
            "info": info,
            "created_at": row["created_at"],
            "priority": priority,
        })

    # 우선순위 높은 것 먼저, 같으면 시간순
    scored.sort(key=lambda x: (-x["priority"], x["id"]))

    selected = scored[:tweets_per_day]
    # 최종 결과는 시간순으로
    selected.sort(key=lambda x: x["id"])

    # 타임라인 형태로 변환
    tweets = []
    for item in selected:
        tweet = _format_tweet(item, day, minutes_per_round)
        if tweet:
            tweets.append(tweet)

    return {"day": day, "tweets": tweets}


def get_profiles_from_db(db_path: str) -> Dict[int, Dict]:
    """DB에서 user 프로필 정보를 가져옴 (없으면 빈 dict)"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM user").fetchall()
        conn.close()
        return {row["user_id"]: dict(row) for row in rows}
    except Exception:
        return {}


def _format_tweet(item: Dict, day: int, minutes_per_round: int) -> Optional[Dict]:
    """액션을 타임라인 트윗 형태로 변환"""
    action = item["action"].lower() if item["action"] else ""
    info = item["info"]

    if action == "create_post":
        content = info.get("content", info.get("post", ""))
        if not content and isinstance(info, dict):
            # Try to find content in nested structures
            for key in ["text", "body", "message"]:
                if key in info:
                    content = info[key]
                    break
        return {
            "type": "post",
            "user_id": item["user_id"],
            "content": content or "(empty post)",
            "likes": 0,
            "reposts": 0,
            "comments": 0,
            "time": _sim_time(item["id"], day, minutes_per_round),
        }

    elif action == "quote_post":
        content = info.get("content", "")
        original = info.get("original_post", info.get("quoted_content", ""))
        return {
            "type": "quote",
            "user_id": item["user_id"],
            "content": content,
            "quoted_content": original,
            "likes": 0,
            "reposts": 0,
            "time": _sim_time(item["id"], day, minutes_per_round),
        }

    elif action == "create_comment":
        content = info.get("content", info.get("comment", ""))
        return {
            "type": "comment",
            "user_id": item["user_id"],
            "content": content,
            "parent_post": info.get("parent_post", ""),
            "time": _sim_time(item["id"], day, minutes_per_round),
        }

    elif action == "repost":
        return {
            "type": "repost",
            "user_id": item["user_id"],
            "original_content": info.get("content", info.get("original_content", "")),
            "original_author": info.get("original_author", ""),
            "time": _sim_time(item["id"], day, minutes_per_round),
        }

    elif action == "like_post":
        return {
            "type": "like",
            "user_id": item["user_id"],
            "liked_content": info.get("content", info.get("post_content", "")),
            "liked_author": info.get("author", info.get("post_author_name", "")),
            "time": _sim_time(item["id"], day, minutes_per_round),
        }

    return None


def _sim_time(action_id: int, day: int, minutes_per_round: int) -> str:
    """액션 ID 기반으로 대략적인 시뮬 시간 생성"""
    # 간단하게 하루 내에서 분산
    hour = 8 + (action_id % 14)  # 8시~22시 사이
    minute = (action_id * 17) % 60
    return f"{hour:02d}:{minute:02d}"
