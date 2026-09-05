import http from './http'


export async function getRecommend(previousSuggestion = '') {
  const { data } = await http.post('/recommend', {
    previous_suggestion: previousSuggestion || null,
  })
  return data
}


export async function acceptRecommendation(id, payload = {}) {
  const { data } = await http.post(`/recommendations/${id}/accept`, payload)
  return data
}


export async function getPendingFeedback() {
  const { data } = await http.get('/recommendations/pending_feedback')
  return data
}


export async function submitRecommendationFeedback(id, payload) {
  const { data } = await http.post(`/recommendations/${id}/feedback`, payload)
  return data.recommendation || data
}


export async function getRecommendationHistory() {
  const { data } = await http.get('/recommendations/history')
  return data
}


export async function deleteRecommendation(id) {
  const { data } = await http.delete(`/recommendations/${id}`)
  return data
}
