
export type HealthLanguage = 'English' | 'Hindi' | 'Marathi'

export interface AskRequest {
  question: string
  language?: HealthLanguage
}

export interface AskSource {
  title: string
  url: string
}

export interface AskResponse {
  answer: string
  sources: AskSource[]
  disclaimer: string
  should_consult_doctor: boolean
  urgent: boolean
}

export interface NmcDoctorResult {
  name: string | null
  registration_number: string | null
  council: string | null
  registration_date: string | null
  qualification: string | null
  registration_status: string | null
  source_url: string | null
  retrieved_at: string
  verification_status: 'unverified'
}

export interface NmcLookupResponse {
  results: NmcDoctorResult[]
  retrieved_at: string
  verification_notice: string
}

export interface NmcSearchRequest {
  name?: string
  registration_number?: string
  council?: string
}

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

const ASK_ERROR_MESSAGE =
  "We couldn't connect to the health assistant right now. Please try again."

export async function askHealthQuestion(
  request: AskRequest
): Promise<AskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...request,
      language: request.language ?? 'English',
    }),
  })

  if (!response.ok) {
    throw new Error(ASK_ERROR_MESSAGE)
  }

  return response.json() as Promise<AskResponse>
}

export async function lookupDoctorRegistration(
  request: NmcSearchRequest
): Promise<NmcLookupResponse> {
  const response = await fetch(`${API_BASE_URL}/api/doctors/registration-lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { error?: { message?: string } }
      | null
    throw new Error(
      body?.error?.message ??
        'We couldn’t complete the registration search. Please try again.'
    )
  }

  return response.json() as Promise<NmcLookupResponse>
}
