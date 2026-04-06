<template>
  <div class="timeline-page">
    <div class="container">
      <!-- Header -->
      <header class="tl-header">
        <button class="back-btn" @click="$router.push('/')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M7.414 13l5.043 5.04-1.414 1.42L3.586 12l7.457-7.46 1.414 1.42L7.414 11H21v2H7.414z"/>
          </svg>
        </button>
        <div>
          <h1 class="tl-title">SimTwit</h1>
          <p class="tl-subtitle" v-if="mainProfile">{{ mainProfile.name }}의 트위터</p>
        </div>
        <button class="share-btn" @click="copyUrl">
          {{ copied ? 'Copied!' : '공유' }}
        </button>
      </header>

      <!-- Status: Loading/Running -->
      <div v-if="status === 'running'" class="status-banner">
        <div class="spinner"></div>
        <span>시뮬레이션 진행 중... 잠시 후 새로고침 해주세요</span>
      </div>

      <!-- Profile Card -->
      <div v-if="mainProfile" class="profile-card">
        <div class="avatar">{{ mainProfile.name?.charAt(0) }}</div>
        <div class="profile-info">
          <div class="profile-name">{{ mainProfile.name }}</div>
          <div class="profile-handle">@{{ mainProfile.username }}</div>
          <div class="profile-bio">{{ mainProfile.bio }}</div>
        </div>
      </div>

      <!-- Day Tabs -->
      <div class="day-tabs">
        <button
          v-for="d in 7"
          :key="d"
          class="day-tab"
          :class="{ active: d === currentDay, locked: d > maxDay }"
          @click="d <= maxDay && selectDay(d)"
        >
          {{ d > maxDay ? '🔒' : '' }} Day {{ d }}
        </button>
      </div>

      <!-- Tweets -->
      <div v-if="tweets.length === 0 && status === 'completed'" class="empty">
        이 날은 아직 트윗이 없습니다.
      </div>

      <div v-for="tweet in tweets" :key="tweet.id || tweet.time" class="tweet">
        <!-- Post -->
        <template v-if="tweet.type === 'post'">
          <div class="tweet-header">
            <div class="tweet-avatar">{{ getAuthorName(tweet).charAt(0) }}</div>
            <div>
              <span class="tweet-name">{{ getAuthorName(tweet) }}</span>
              <span class="tweet-handle">@{{ getAuthorHandle(tweet) }}</span>
            </div>
            <span class="tweet-time">{{ tweet.time }}</span>
          </div>
          <div class="tweet-content">{{ tweet.content }}</div>
          <div class="tweet-actions">
            <span class="action-btn">💬 {{ tweet.comments || 0 }}</span>
            <span class="action-btn">🔁 {{ tweet.reposts || 0 }}</span>
            <span class="action-btn">♡ {{ tweet.likes || 0 }}</span>
            <span class="action-btn copy-btn" @click="copyTweet(tweet)">📋</span>
          </div>
        </template>

        <!-- Quote -->
        <template v-else-if="tweet.type === 'quote'">
          <div class="tweet-header">
            <div class="tweet-avatar">{{ getAuthorName(tweet).charAt(0) }}</div>
            <div>
              <span class="tweet-name">{{ getAuthorName(tweet) }}</span>
              <span class="tweet-handle">@{{ getAuthorHandle(tweet) }}</span>
            </div>
            <span class="tweet-time">{{ tweet.time }}</span>
          </div>
          <div class="tweet-content">{{ tweet.content }}</div>
          <div class="quoted-tweet" v-if="tweet.quoted_content">
            <div class="quoted-content">{{ tweet.quoted_content }}</div>
          </div>
          <div class="tweet-actions">
            <span class="action-btn">♡ {{ tweet.likes || 0 }}</span>
            <span class="action-btn">🔁 {{ tweet.reposts || 0 }}</span>
          </div>
        </template>

        <!-- Comment -->
        <template v-else-if="tweet.type === 'comment'">
          <div class="tweet-header">
            <div class="tweet-avatar comment-avatar">{{ getAuthorName(tweet).charAt(0) }}</div>
            <div>
              <span class="tweet-name">{{ getAuthorName(tweet) }}</span>
              <span class="tweet-handle">@{{ getAuthorHandle(tweet) }}</span>
              <span class="reply-label">님의 답글</span>
            </div>
            <span class="tweet-time">{{ tweet.time }}</span>
          </div>
          <div class="tweet-content">{{ tweet.content }}</div>
        </template>

        <!-- Repost -->
        <template v-else-if="tweet.type === 'repost'">
          <div class="repost-label">🔁 {{ getAuthorName(tweet) }} 님이 리포스트</div>
          <div class="tweet-content reposted">{{ tweet.original_content }}</div>
        </template>

        <!-- Like -->
        <template v-else-if="tweet.type === 'like'">
          <div class="like-label">♡ {{ getAuthorName(tweet) }} 님이 좋아합니다</div>
          <div class="tweet-content liked-content">{{ tweet.liked_content }}</div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import { getFeed, getStatus, getProfiles } from '../api'

export default {
  data() {
    return {
      simId: '',
      status: 'loading',
      currentDay: 1,
      maxDay: 7,
      tweets: [],
      profiles: [],
      profilesMap: {},
      copied: false,
    }
  },
  computed: {
    mainProfile() {
      return this.profiles.find((p) => !p.is_npc)
    },
  },
  async mounted() {
    this.simId = this.$route.params.simId
    await this.checkStatus()
    await this.loadProfiles()
    await this.loadFeed(1)
  },
  methods: {
    async checkStatus() {
      try {
        const res = await getStatus(this.simId)
        this.status = res.data.status
        if (this.status === 'running') {
          setTimeout(() => this.checkStatus(), 5000)
        }
      } catch {
        this.status = 'error'
      }
    },
    async loadProfiles() {
      try {
        const res = await getProfiles(this.simId)
        this.profiles = res.data.profiles || []
        this.profilesMap = {}
        for (const p of this.profiles) {
          this.profilesMap[p.user_id] = p
        }
      } catch {
        // profiles not ready yet
      }
    },
    async loadFeed(day) {
      try {
        const res = await getFeed(this.simId, day, 5)
        this.tweets = res.data.tweets || []
        this.currentDay = day
      } catch {
        this.tweets = []
      }
    },
    selectDay(day) {
      this.loadFeed(day)
    },
    getAuthorName(tweet) {
      if (tweet.author?.name) return tweet.author.name
      const p = this.profilesMap[tweet.user_id]
      return p?.name || `User ${tweet.user_id}`
    },
    getAuthorHandle(tweet) {
      if (tweet.author?.username) return tweet.author.username
      const p = this.profilesMap[tweet.user_id]
      return p?.username || `user_${tweet.user_id}`
    },
    copyUrl() {
      navigator.clipboard.writeText(window.location.href)
      this.copied = true
      setTimeout(() => (this.copied = false), 2000)
    },
    copyTweet(tweet) {
      const name = this.getAuthorName(tweet)
      const text = `${name}: ${tweet.content}\n\n— SimTwit (${window.location.href})`
      navigator.clipboard.writeText(text)
    },
  },
}
</script>

<style scoped>
.timeline-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  padding: 0;
}
.container {
  max-width: 600px;
  width: 100%;
  border-left: 1px solid #2f3336;
  border-right: 1px solid #2f3336;
  min-height: 100vh;
}

/* Header */
.tl-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #2f3336;
  position: sticky;
  top: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  z-index: 10;
}
.back-btn {
  background: none;
  border: none;
  color: #e7e9ea;
  cursor: pointer;
  padding: 4px;
}
.tl-title {
  font-size: 18px;
  font-weight: 700;
  color: #1d9bf0;
}
.tl-subtitle {
  font-size: 13px;
  color: #71767b;
}
.share-btn {
  margin-left: auto;
  background: none;
  border: 1px solid #536471;
  color: #e7e9ea;
  border-radius: 9999px;
  padding: 6px 16px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}
.share-btn:hover {
  background: rgba(239, 243, 244, 0.1);
}

/* Status */
.status-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #1d1f23;
  border-bottom: 1px solid #2f3336;
  color: #71767b;
  font-size: 14px;
}
.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #2f3336;
  border-top-color: #1d9bf0;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Profile Card */
.profile-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #2f3336;
}
.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #1d9bf0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.profile-name {
  font-weight: 700;
  font-size: 15px;
}
.profile-handle {
  color: #71767b;
  font-size: 14px;
}
.profile-bio {
  font-size: 14px;
  margin-top: 4px;
  color: #e7e9ea;
}

/* Day Tabs */
.day-tabs {
  display: flex;
  border-bottom: 1px solid #2f3336;
  overflow-x: auto;
}
.day-tab {
  flex: 1;
  min-width: 70px;
  padding: 12px 8px;
  text-align: center;
  background: none;
  border: none;
  color: #71767b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.day-tab.active {
  color: #e7e9ea;
  border-bottom-color: #1d9bf0;
  font-weight: 700;
}
.day-tab.locked {
  color: #536471;
  cursor: default;
}
.day-tab:hover:not(.locked):not(.active) {
  background: rgba(239, 243, 244, 0.03);
}

/* Tweets */
.tweet {
  padding: 12px 16px;
  border-bottom: 1px solid #2f3336;
}
.tweet-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.tweet-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #2f3336;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: #e7e9ea;
  flex-shrink: 0;
}
.comment-avatar {
  width: 32px;
  height: 32px;
  font-size: 13px;
}
.tweet-name {
  font-weight: 700;
  font-size: 15px;
}
.tweet-handle {
  color: #71767b;
  font-size: 14px;
  margin-left: 4px;
}
.reply-label {
  color: #71767b;
  font-size: 13px;
  margin-left: 4px;
}
.tweet-time {
  margin-left: auto;
  color: #71767b;
  font-size: 13px;
}
.tweet-content {
  font-size: 15px;
  line-height: 1.5;
  margin: 8px 0;
  white-space: pre-wrap;
}
.tweet-actions {
  display: flex;
  gap: 24px;
  margin-top: 8px;
}
.action-btn {
  color: #71767b;
  font-size: 13px;
  cursor: pointer;
}
.action-btn:hover {
  color: #1d9bf0;
}
.copy-btn {
  margin-left: auto;
}

/* Quote */
.quoted-tweet {
  border: 1px solid #2f3336;
  border-radius: 12px;
  padding: 12px;
  margin: 8px 0;
}
.quoted-content {
  font-size: 14px;
  color: #e7e9ea;
}

/* Repost / Like labels */
.repost-label,
.like-label {
  font-size: 13px;
  color: #71767b;
  margin-bottom: 4px;
}
.reposted,
.liked-content {
  font-size: 14px;
  color: #71767b;
  font-style: italic;
}

/* Empty */
.empty {
  text-align: center;
  padding: 40px 16px;
  color: #71767b;
  font-size: 15px;
}
</style>
