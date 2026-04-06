"""
SimTwit Twitter 시뮬레이션 실행 스크립트

OASIS를 사용하여 가상 트위터 시뮬레이션을 실행한다.
MiroFish의 run_twitter_simulation.py를 SimTwit 용도로 간소화.

Usage:
    python run_simulation.py --config /path/to/simulation_config.json
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime
from typing import Dict, Any, List

# Load .env
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(asctime)s - %(name)s - %(message)s",
)
# Suppress noisy camel-ai warnings
logging.getLogger().addFilter(
    type('F', (logging.Filter,), {
        'filter': lambda self, r: 'max_tokens' not in r.getMessage()
    })()
)

try:
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    import oasis
    from oasis import ActionType, LLMAction, generate_twitter_agent_graph
except ImportError as e:
    print(f"Error: missing dependency {e}")
    print("Install: pip install oasis-ai camel-ai")
    sys.exit(1)


AVAILABLE_ACTIONS = [
    ActionType.CREATE_POST,
    ActionType.LIKE_POST,
    ActionType.REPOST,
    ActionType.FOLLOW,
    ActionType.DO_NOTHING,
    ActionType.QUOTE_POST,
]


def create_model():
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "")
    model_name = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_API_BASE_URL"] = base_url

    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("LLM_API_KEY not configured in .env")

    print(f"LLM: model={model_name}, base_url={base_url[:40] if base_url else 'default'}...")
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=model_name,
    )


def get_active_agents(config: Dict, agent_graph, current_hour: int) -> List:
    """시간대에 따라 활성 에이전트 선정"""
    time_config = config.get("time_config", {})
    agent_configs = config.get("agent_configs", [])
    peak_hours = time_config.get("peak_hours", [10, 11, 14, 20, 21, 22])
    off_peak_hours = time_config.get("off_peak_hours", [0, 1, 2, 3, 4, 5])

    if current_hour in peak_hours:
        multiplier = time_config.get("peak_activity_multiplier", 1.5)
    elif current_hour in off_peak_hours:
        multiplier = time_config.get("off_peak_activity_multiplier", 0.1)
    else:
        multiplier = 1.0

    base_min = time_config.get("agents_per_hour_min", 1)
    base_max = time_config.get("agents_per_hour_max", 4)
    target = int(random.uniform(base_min, base_max) * multiplier)

    candidates = []
    for cfg in agent_configs:
        agent_id = cfg.get("agent_id", 0)
        active_hours = cfg.get("active_hours", list(range(8, 23)))
        activity_level = cfg.get("activity_level", 0.5)

        if current_hour not in active_hours:
            continue
        if random.random() < activity_level:
            candidates.append(agent_id)

    selected_ids = random.sample(candidates, min(target, len(candidates))) if candidates else []

    agents = []
    for aid in selected_ids:
        try:
            agent = agent_graph.get_agent(aid)
            agents.append(agent)
        except Exception:
            pass
    return agents


async def run_simulation(config_path: str, max_rounds: int = None):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    sim_dir = os.path.dirname(config_path)
    sim_id = config.get("simulation_id", "unknown")
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 168)
    minutes_per_round = time_config.get("minutes_per_round", 60)
    total_rounds = (total_hours * 60) // minutes_per_round

    if max_rounds and max_rounds > 0:
        total_rounds = min(total_rounds, max_rounds)

    print("=" * 50)
    print(f"SimTwit Simulation: {sim_id}")
    print(f"  Hours: {total_hours}, Rounds: {total_rounds}, Agents: {len(config.get('agent_configs', []))}")
    print("=" * 50)

    model = create_model()

    profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
    if not os.path.exists(profile_path):
        print(f"Error: profile not found: {profile_path}")
        return

    agent_graph = await generate_twitter_agent_graph(
        profile_path=profile_path,
        model=model,
        available_actions=AVAILABLE_ACTIONS,
    )

    db_path = os.path.join(sim_dir, "twitter_simulation.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,
        database_path=db_path,
        semaphore=30,
    )
    await env.reset()
    print("Environment ready.\n")

    # Initial posts
    event_config = config.get("event_config", {})
    for post in event_config.get("initial_posts", []):
        try:
            from oasis import ManualAction
            agent = agent_graph.get_agent(post.get("poster_agent_id", 0))
            await env.step({agent: ManualAction(
                action_type=ActionType.CREATE_POST,
                action_args={"content": post["content"]},
            )})
        except Exception as e:
            print(f"  Warning: initial post failed: {e}")

    # Main loop
    start = datetime.now()
    for rnd in range(total_rounds):
        sim_minutes = rnd * minutes_per_round
        sim_hour = (sim_minutes // 60) % 24
        sim_day = sim_minutes // (60 * 24) + 1

        agents = get_active_agents(config, agent_graph, sim_hour)
        if not agents:
            continue

        actions = {agent: LLMAction() for agent in agents}
        await env.step(actions)

        if (rnd + 1) % 10 == 0 or rnd == 0:
            elapsed = (datetime.now() - start).total_seconds()
            pct = (rnd + 1) / total_rounds * 100
            print(f"  [Day {sim_day}, {sim_hour:02d}:00] Round {rnd+1}/{total_rounds} ({pct:.0f}%) "
                  f"- {len(agents)} agents - {elapsed:.0f}s")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nDone! {elapsed:.0f}s total. DB: {db_path}")

    # Write completion marker
    with open(os.path.join(sim_dir, "status.json"), "w") as f:
        json.dump({"status": "completed", "db_path": db_path}, f)

    await env.close()


def main():
    parser = argparse.ArgumentParser(description='SimTwit Simulation')
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--max-rounds', type=int, default=None)
    args = parser.parse_args()

    asyncio.run(run_simulation(args.config, args.max_rounds))


if __name__ == "__main__":
    main()
