import http from './http'


export async function getReportSummary(period, date) {
  const { data } = await http.get('/reports/summary', {
    params: { period, date },
  })
  return data
}
