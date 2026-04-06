"""
SimTwit API Routes

POST /api/world/create    - 캐릭터 설정 → 시뮬 생성/실행
GET  /api/world/<id>/feed - 일자별 타임라인 피드
GET  /api/world/<id>/status - 시뮬레이션 상태
GET  /api/world/<id>/profiles - 에이전트 프로필 목록
"""

import json
import os
import subprocess
import sys
import uuid
from flask import request, jsonify

from . import simtwit_bp
from ..services.profile_builder import ProfileBuilder, CharacterInput
from ..services.sim_config import generate_config
from ..services.tweet_curator import get_timeline

# 시뮬레이션 데이터 디렉토리
SIM_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../uploads/simulations')
)
SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../scripts')
)


@simtwit_bp.route('/world/create', methods=['POST'])
def create_world():
    """
    캐릭터 설정을 받아서 시뮬레이션을 생성하고 실행한다.

    Request body:
    {
        "name": "Warren Buffett",
        "mbti": "ISTJ",
        "job": "Investor",
        "bio": "The Oracle of Omaha, back from the beyond",
        "interests": ["investing", "value investing", "Coca-Cola"],
        "situation": "워렌버핏이 부활해서 처음으로 트위터를 시작했다",
        "total_hours": 168,
        "max_rounds": null
    }
    """
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    # 1. 시뮬레이션 ID & 디렉토리 생성
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"
    sim_dir = os.path.join(SIM_DATA_DIR, sim_id)
    os.makedirs(sim_dir, exist_ok=True)

    # 2. 캐릭터 입력 구성
    char = CharacterInput(
        name=data["name"],
        mbti=data.get("mbti", ""),
        job=data.get("job", ""),
        bio=data.get("bio", ""),
        interests=data.get("interests", []),
        situation=data.get("situation", ""),
    )

    # 3. 프로필 생성 (LLM 호출)
    builder = ProfileBuilder()
    try:
        profiles = builder.build(char, sim_dir)
    except Exception as e:
        return jsonify({"error": f"Profile generation failed: {e}"}), 500

    # 4. Config 생성
    total_hours = data.get("total_hours", 168)
    config = generate_config(sim_id, profiles, sim_dir, total_hours=total_hours)

    # 5. 시뮬레이션을 백그라운드 프로세스로 실행
    script_path = os.path.join(SCRIPTS_DIR, "run_simulation.py")
    config_path = os.path.join(sim_dir, "simulation_config.json")

    cmd = [sys.executable, script_path, "--config", config_path]
    max_rounds = data.get("max_rounds")
    if max_rounds:
        cmd.extend(["--max-rounds", str(max_rounds)])

    # status 파일 초기화
    with open(os.path.join(sim_dir, "status.json"), "w") as f:
        json.dump({"status": "running"}, f)

    # stdout/stderr를 파일로 리다이렉트
    stdout_file = open(os.path.join(sim_dir, "stdout.log"), "w")
    stderr_file = open(os.path.join(sim_dir, "stderr.log"), "w")

    process = subprocess.Popen(
        cmd,
        stdout=stdout_file,
        stderr=stderr_file,
        cwd=SCRIPTS_DIR,
    )

    return jsonify({
        "simulation_id": sim_id,
        "status": "running",
        "pid": process.pid,
        "profiles": [
            {"user_id": p.user_id, "name": p.name, "username": p.username,
             "bio": p.bio, "is_npc": p.is_npc}
            for p in profiles
        ],
        "total_hours": total_hours,
        "total_rounds": (total_hours * 60) // config["time_config"]["minutes_per_round"],
    })


@simtwit_bp.route('/world/<sim_id>/status', methods=['GET'])
def get_status(sim_id):
    """시뮬레이션 상태 확인"""
    sim_dir = os.path.join(SIM_DATA_DIR, sim_id)
    status_path = os.path.join(sim_dir, "status.json")

    if not os.path.exists(status_path):
        return jsonify({"error": "simulation not found"}), 404

    with open(status_path, "r") as f:
        status = json.load(f)

    return jsonify({"simulation_id": sim_id, **status})


@simtwit_bp.route('/world/<sim_id>/feed', methods=['GET'])
def get_feed(sim_id):
    """
    일자별 타임라인 피드.

    Query params:
        day: 일차 (1~7, default 1)
        count: 하루 트윗 수 (default 5)
    """
    sim_dir = os.path.join(SIM_DATA_DIR, sim_id)
    db_path = os.path.join(sim_dir, "twitter_simulation.db")

    if not os.path.exists(db_path):
        return jsonify({"error": "simulation DB not found (still running?)"}), 404

    day = request.args.get("day", 1, type=int)
    count = request.args.get("count", 5, type=int)
    day = max(1, min(day, 7))

    timeline = get_timeline(db_path, day, tweets_per_day=count)

    # 프로필 정보 합치기
    profiles_path = os.path.join(sim_dir, "profiles.json")
    profiles_map = {}
    if os.path.exists(profiles_path):
        with open(profiles_path, "r", encoding="utf-8") as f:
            for p in json.load(f):
                profiles_map[p["user_id"]] = {
                    "name": p["name"],
                    "username": p["username"],
                    "bio": p["bio"],
                    "is_npc": p["is_npc"],
                }

    # 트윗에 프로필 정보 추가
    for tweet in timeline.get("tweets", []):
        uid = tweet.get("user_id")
        if uid in profiles_map:
            tweet["author"] = profiles_map[uid]

    return jsonify({"simulation_id": sim_id, **timeline})


@simtwit_bp.route('/world/<sim_id>/profiles', methods=['GET'])
def get_profiles(sim_id):
    """에이전트 프로필 목록"""
    sim_dir = os.path.join(SIM_DATA_DIR, sim_id)
    profiles_path = os.path.join(sim_dir, "profiles.json")

    if not os.path.exists(profiles_path):
        return jsonify({"error": "profiles not found"}), 404

    with open(profiles_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    return jsonify({"simulation_id": sim_id, "profiles": profiles})
