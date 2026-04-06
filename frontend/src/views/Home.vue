<template>
  <div class="home">
    <div class="container">
      <header class="header">
        <h1 class="logo">SimTwit</h1>
        <p class="tagline">AI 캐릭터가 매일 글을 올리는 가상 트위터</p>
      </header>

      <!-- Presets -->
      <section class="presets">
        <h2>인기 프리셋</h2>
        <div class="preset-grid">
          <button
            v-for="preset in presets"
            :key="preset.name"
            class="preset-card"
            @click="fillPreset(preset)"
          >
            <span class="preset-emoji">{{ preset.emoji }}</span>
            <span class="preset-name">{{ preset.label }}</span>
          </button>
        </div>
      </section>

      <!-- Character Form -->
      <section class="form-section">
        <h2>캐릭터 설정</h2>
        <form @submit.prevent="submit">
          <div class="field">
            <label>이름 *</label>
            <input v-model="form.name" placeholder="e.g. Warren Buffett" required />
          </div>
          <div class="row">
            <div class="field">
              <label>MBTI</label>
              <input v-model="form.mbti" placeholder="e.g. ISTJ" />
            </div>
            <div class="field">
              <label>직업</label>
              <input v-model="form.job" placeholder="e.g. Investor" />
            </div>
          </div>
          <div class="field">
            <label>한 줄 소개</label>
            <input v-model="form.bio" placeholder="e.g. 오마하의 현인" />
          </div>
          <div class="field">
            <label>관심사 (쉼표 구분)</label>
            <input v-model="interestsStr" placeholder="e.g. 투자, 가치투자, 코카콜라" />
          </div>
          <div class="field">
            <label>상황 설정</label>
            <input v-model="form.situation" placeholder="e.g. 부활해서 처음으로 트위터를 시작했다" />
          </div>

          <button type="submit" class="submit-btn" :disabled="loading">
            {{ loading ? '생성 중...' : '시뮬레이션 시작' }}
          </button>

          <p v-if="error" class="error">{{ error }}</p>
        </form>
      </section>
    </div>
  </div>
</template>

<script>
import { createWorld } from '../api'

export default {
  data() {
    return {
      form: {
        name: '',
        mbti: '',
        job: '',
        bio: '',
        situation: '',
      },
      interestsStr: '',
      loading: false,
      error: '',
      presets: [
        {
          emoji: '💰',
          label: '워렌버핏의 트위터',
          name: 'Warren Buffett',
          mbti: 'ISTJ',
          job: 'Investor & Chairman of Berkshire Hathaway',
          bio: '오마하의 현인, 세계 최고의 가치투자자',
          interests: '가치투자, 주식, 코카콜라, 버크셔해서웨이, 경영',
          situation: '워렌버핏이 다시 살아나서 처음으로 트위터를 직접 시작했다',
        },
        {
          emoji: '🧠',
          label: '제갈량이 현대에 왔다면',
          name: '제갈량',
          mbti: 'INTJ',
          job: '전략가',
          bio: '삼국시대 촉한의 승상, 현대에 타임슬립',
          interests: '병법, 전략, 정치, 역사, 기술',
          situation: '조선시대가 아닌 현대 한국에 갑자기 떨어졌다',
        },
        {
          emoji: '🔍',
          label: '셜록 홈즈의 트위터',
          name: 'Sherlock Holmes',
          mbti: 'INTP',
          job: 'Consulting Detective',
          bio: '221B 베이커 스트리트의 자문 탐정',
          interests: '추리, 범죄학, 바이올린, 화학, 관찰',
          situation: '빅토리아 시대에서 현대 런던으로 와서 트위터를 시작했다',
        },
        {
          emoji: '🎮',
          label: 'INFP 대학생의 7일',
          name: '김하늘',
          mbti: 'INFP',
          job: '대학생 (문예창작과)',
          bio: '글 쓰고 음악 듣고 고양이 좋아하는 내향인',
          interests: '글쓰기, 음악, 고양이, 카페, 영화',
          situation: '기말고사가 끝나고 방학이 시작된 첫 주',
        },
      ],
    }
  },
  methods: {
    fillPreset(preset) {
      this.form.name = preset.name
      this.form.mbti = preset.mbti
      this.form.job = preset.job
      this.form.bio = preset.bio
      this.form.situation = preset.situation
      this.interestsStr = preset.interests
    },
    async submit() {
      if (!this.form.name) return
      this.loading = true
      this.error = ''

      try {
        const payload = {
          ...this.form,
          interests: this.interestsStr
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
        }
        const res = await createWorld(payload)
        const simId = res.data.simulation_id
        this.$router.push(`/t/${simId}`)
      } catch (e) {
        this.error = e.response?.data?.error || e.message
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  padding: 40px 16px;
}
.container {
  max-width: 520px;
  width: 100%;
}
.header {
  text-align: center;
  margin-bottom: 32px;
}
.logo {
  font-size: 32px;
  font-weight: 700;
  color: #1d9bf0;
}
.tagline {
  color: #71767b;
  margin-top: 8px;
  font-size: 15px;
}

.presets {
  margin-bottom: 32px;
}
.presets h2 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 12px;
  color: #e7e9ea;
}
.preset-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.preset-card {
  background: #16181c;
  border: 1px solid #2f3336;
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #e7e9ea;
  transition: background 0.15s;
}
.preset-card:hover {
  background: #1d1f23;
}
.preset-emoji {
  font-size: 20px;
}

.form-section h2 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #e7e9ea;
}
.field {
  margin-bottom: 12px;
}
.field label {
  display: block;
  font-size: 13px;
  color: #71767b;
  margin-bottom: 4px;
}
.field input {
  width: 100%;
  background: #16181c;
  border: 1px solid #2f3336;
  border-radius: 8px;
  padding: 10px 12px;
  color: #e7e9ea;
  font-size: 15px;
  outline: none;
}
.field input:focus {
  border-color: #1d9bf0;
}
.row {
  display: flex;
  gap: 12px;
}
.row .field {
  flex: 1;
}

.submit-btn {
  width: 100%;
  background: #1d9bf0;
  color: #fff;
  border: none;
  border-radius: 9999px;
  padding: 12px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  margin-top: 8px;
  transition: background 0.15s;
}
.submit-btn:hover:not(:disabled) {
  background: #1a8cd8;
}
.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.error {
  color: #f4212e;
  font-size: 14px;
  margin-top: 8px;
  text-align: center;
}
</style>
