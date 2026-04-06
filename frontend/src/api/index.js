import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export function createWorld(data) {
  return api.post('/world/create', data)
}

export function getStatus(simId) {
  return api.get(`/world/${simId}/status`)
}

export function getFeed(simId, day = 1, count = 5) {
  return api.get(`/world/${simId}/feed`, { params: { day, count } })
}

export function getProfiles(simId) {
  return api.get(`/world/${simId}/profiles`)
}
