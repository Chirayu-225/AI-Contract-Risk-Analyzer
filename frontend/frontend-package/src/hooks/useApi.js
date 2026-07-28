// src/hooks/useApi.js
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const analyzeContract = async (file, partyAName, partyBName, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  form.append('party_a_name', partyAName || 'Party A (You)')
  form.append('party_b_name', partyBName || 'Party B (Counterparty)')

  onProgress?.('Extracting contract text...')
  const { data } = await api.post('/analyze', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  })
  return data
}

export const listAnalyses = async () => {
  const { data } = await api.get('/analyses')
  return data
}

export const getAnalysis = async (id) => {
  const { data } = await api.get(`/analyses/${id}`)
  return data
}

export const getReportUrl = (id) => `/api/analyses/${id}/report`
