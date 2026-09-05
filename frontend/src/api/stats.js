import http from './http'


export async function getTags() {
  const { data } = await http.get('/tags')
  return data
}



export async function getStats(tagName, { start_date, end_date } = {}) {
  const { data } = await http.get(`/stats/${encodeURIComponent(tagName)}`, {
    params: { start_date, end_date },
  })
  return data
}



export async function getDailyAvg({ start_date, end_date } = {}) {
  const { data } = await http.get('/stats/daily_avg', {
    params: { start_date, end_date },
  })
  return data
}