"""
캐릭터 프로필 입력 → OASIS Twitter CSV 프로필 생성

사용자 입력(이름, MBTI, 직업 등)을 받아서
LLM으로 풍성한 페르소나를 만들고, NPC 2~3명도 자동 생성한 뒤
OASIS가 요구하는 twitter_profiles.csv 형태로 저장한다.
"""

import csv
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

from openai import OpenAI


@dataclass
class CharacterInput:
    """사용자가 입력하는 캐릭터 설정"""
    name: str
    mbti: str = ""
    job: str = ""
    bio: str = ""
    interests: List[str] = field(default_factory=list)
    situation: str = ""  # e.g. "조선시대에서 현대로 옴", "퇴사 직후"


@dataclass
class AgentProfile:
    """OASIS Twitter Agent 프로필"""
    user_id: int
    username: str
    name: str
    bio: str
    persona: str
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    created_at: str = "2025-01-01"
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: Optional[str] = None
    is_npc: bool = False


class ProfileBuilder:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ.get("LLM_API_KEY", ""),
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
        self.model = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

    def build(self, character: CharacterInput, sim_dir: str) -> List[AgentProfile]:
        """메인 캐릭터 + NPC 프로필을 생성하고 CSV로 저장"""
        profiles = self._generate_profiles(character)
        self._save_csv(profiles, os.path.join(sim_dir, "twitter_profiles.csv"))
        # JSON도 저장 (디버깅/API 응답용)
        self._save_json(profiles, os.path.join(sim_dir, "profiles.json"))
        return profiles

    def _generate_profiles(self, char: CharacterInput) -> List[AgentProfile]:
        """LLM으로 메인 캐릭터 페르소나 + NPC 생성"""
        interests_str = ", ".join(char.interests) if char.interests else "not specified"

        prompt = f"""You are creating character profiles for a simulated Twitter environment.

Main character:
- Name: {char.name}
- MBTI: {char.mbti or 'not specified'}
- Job: {char.job or 'not specified'}
- Bio: {char.bio or 'not specified'}
- Interests: {interests_str}
- Situation: {char.situation or 'not specified'}

Generate the following as JSON:

1. "main": A rich persona for the main character. Write 3-5 sentences describing their personality, speaking style, values, and how they would behave on Twitter. Also generate a short Twitter bio (under 160 chars).

2. "npcs": Generate exactly 3 NPC followers who would naturally interact with this character. For each NPC provide:
   - name, username, bio, persona (2-3 sentences), age, gender, mbti, profession, interested_topics (semicolon-separated)
   - Each NPC should have a distinct relationship to the main character (e.g. fan, critic, colleague, journalist)

Output ONLY valid JSON with this structure:
{{
  "main": {{
    "bio": "...",
    "persona": "...",
    "age": 93,
    "gender": "Male"
  }},
  "npcs": [
    {{
      "name": "...",
      "username": "...",
      "bio": "...",
      "persona": "...",
      "age": 30,
      "gender": "Female",
      "mbti": "ENTJ",
      "profession": "...",
      "interested_topics": "finance;investing;stocks"
    }}
  ]
}}

IMPORTANT: All persona and bio text must be in Korean. NPCs should have Korean-style names if the main character context is Korean, otherwise match the cultural context."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        data = json.loads(raw)

        profiles: List[AgentProfile] = []

        # Main character
        main = data["main"]
        username = char.name.lower().replace(" ", "_").replace(".", "")
        profiles.append(AgentProfile(
            user_id=0,
            username=username,
            name=char.name,
            bio=main.get("bio", char.bio),
            persona=main.get("persona", ""),
            friend_count=50,
            follower_count=1000,
            statuses_count=0,
            age=main.get("age"),
            gender=main.get("gender"),
            mbti=char.mbti or None,
            profession=char.job or None,
            interested_topics=";".join(char.interests) if char.interests else None,
            is_npc=False,
        ))

        # NPCs
        for i, npc in enumerate(data.get("npcs", [])[:3], start=1):
            profiles.append(AgentProfile(
                user_id=i,
                username=npc.get("username", f"npc_{i}"),
                name=npc.get("name", f"NPC {i}"),
                bio=npc.get("bio", ""),
                persona=npc.get("persona", ""),
                friend_count=npc.get("friend_count", 80),
                follower_count=npc.get("follower_count", 120),
                statuses_count=npc.get("statuses_count", 300),
                age=npc.get("age"),
                gender=npc.get("gender"),
                mbti=npc.get("mbti"),
                profession=npc.get("profession"),
                interested_topics=npc.get("interested_topics"),
                is_npc=True,
            ))

        return profiles

    def _save_csv(self, profiles: List[AgentProfile], path: str):
        """OASIS Twitter가 요구하는 CSV 포맷으로 저장"""
        fieldnames = [
            "user_id", "username", "name", "bio", "persona",
            "friend_count", "follower_count", "statuses_count", "created_at",
            "age", "gender", "mbti", "country", "profession", "interested_topics",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in profiles:
                row = {
                    "user_id": p.user_id,
                    "username": p.username,
                    "name": p.name,
                    "bio": p.bio,
                    "persona": p.persona,
                    "friend_count": p.friend_count,
                    "follower_count": p.follower_count,
                    "statuses_count": p.statuses_count,
                    "created_at": p.created_at,
                    "age": p.age or "",
                    "gender": p.gender or "",
                    "mbti": p.mbti or "",
                    "country": p.country or "",
                    "profession": p.profession or "",
                    "interested_topics": p.interested_topics or "",
                }
                writer.writerow(row)

    def _save_json(self, profiles: List[AgentProfile], path: str):
        data = []
        for p in profiles:
            d = {k: v for k, v in p.__dict__.items()}
            data.append(d)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
