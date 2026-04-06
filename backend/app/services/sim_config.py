"""
시뮬레이션 Config 생성

모드별 고정 템플릿 기반으로 simulation_config.json을 생성한다.
LLM 호출 없이 프로필 정보로 직접 config를 조립.
"""

import json
import os
from typing import List

from .profile_builder import AgentProfile


def generate_config(
    simulation_id: str,
    profiles: List[AgentProfile],
    sim_dir: str,
    total_hours: int = 168,  # 7일
    minutes_per_round: int = 60,
):
    """시뮬레이션 config를 생성하고 JSON으로 저장"""

    agent_configs = []
    for p in profiles:
        # 메인 캐릭터는 더 활발하게
        if not p.is_npc:
            activity_level = 0.8
            posts_per_hour = 2.0
            active_hours = list(range(7, 24))
        else:
            activity_level = 0.5
            posts_per_hour = 1.0
            active_hours = list(range(9, 23))

        agent_configs.append({
            "agent_id": p.user_id,
            "entity_name": p.name,
            "entity_type": "Person",
            "activity_level": activity_level,
            "posts_per_hour": posts_per_hour,
            "comments_per_hour": 1.5,
            "active_hours": active_hours,
            "response_delay_min": 5,
            "response_delay_max": 30,
            "sentiment_bias": 0.0,
            "stance": "neutral",
            "influence_weight": 3.0 if not p.is_npc else 1.0,
        })

    config = {
        "simulation_id": simulation_id,
        "time_config": {
            "total_simulation_hours": total_hours,
            "minutes_per_round": minutes_per_round,
            "agents_per_hour_min": 1,
            "agents_per_hour_max": len(profiles),
            "peak_hours": [10, 11, 14, 20, 21, 22],
            "peak_activity_multiplier": 1.5,
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "off_peak_activity_multiplier": 0.1,
        },
        "agent_configs": agent_configs,
        "event_config": {
            "initial_posts": [],
            "scheduled_events": [],
            "hot_topics": [],
            "narrative_direction": "",
        },
        "twitter_config": {
            "recency_weight": 0.3,
            "popularity_weight": 0.1,
            "relevance_weight": 0.6,
            "viral_threshold": 999,
            "echo_chamber_strength": 0.8,
        },
        "llm_model": os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini"),
        "llm_base_url": os.environ.get("LLM_BASE_URL", ""),
    }

    path = os.path.join(sim_dir, "simulation_config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return config
