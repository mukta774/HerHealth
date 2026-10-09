import { LoaderCircle, Search, Stethoscope } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import Button from '../components/Button'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'
import {
  lookupDoctorRegistration,
  type NmcDoctorResult,
  type NmcSearchRequest,
} from '../services/api'

function displayValue(value: string | null): string {
  return value || 'Not provided by the source'
}

function DoctorResult({ doctor, index }: { doctor: NmcDoctorResult; index: number }) {
  return (
    <Card className="doctor-result">
      <div className="doctor-result-heading">
        <div>
          <div className="eyebrow">Record {index + 1}</div>
          <h2>{doctor.name || 'Name not provided'}</h2>
        </div>
        <span className="unverified-badge">Unverified source data</span>
      </div>
      <dl className="doctor-details">
        <div><dt>Registration number</dt><dd>{displayValue(doctor.registration_number)}</dd></div>
        <div><dt>State medical council</dt><dd>{displayValue(doctor.council)}</dd></div>
        <div><dt>Registration date</dt><dd>{displayValue(doctor.registration_date)}</dd></div>
        <div><dt>Qualification</dt><dd>{displayValue(doctor.qualification)}</dd></div>
        <div><dt>Registration status</dt><dd>{displayValue(doctor.registration_status)}</dd></div>
        <div><dt>Retrieved</dt><dd>{new Date(doctor.retrieved_at).toLocaleString()}</dd></div>
      </dl>
      {doctor.source_url && (
        <a className="doctor-source-link" href={doctor.source_url} target="_blank" rel="noreferrer">
          View source record
        </a>
      )}
    </Card>
  )
}

export default function Doctors() {
  const [search, setSearch] = useState<NmcSearchRequest>({
    name: '',
    registration_number: '',
    council: '',
  })
  const [results, setResults] = useState<NmcDoctorResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const request = Object.fromEntries(
      Object.entries(search).filter(([, value]) => value?.trim())
    ) as NmcSearchRequest
    if (!Object.keys(request).length) {
      setError('Enter a doctor’s name, registration number, or state medical council.')
      setResults(null)
      return
    }

    setLoading(true)
    setError('')
    setResults(null)
    try {
      const response = await lookupDoctorRegistration(request)
      setResults(response.results)
    } catch (lookupError) {
      setError(
        lookupError instanceof Error
          ? lookupError.message
          : 'We couldn’t complete the registration search. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Care when you need it"
        title="Doctor registration lookup"
        description="Search available medical register data by doctor name, registration number, or state medical council."
        icon={Stethoscope}
      />
      <Card>
        <form className="doctor-search-form" onSubmit={submitSearch}>
          <label className="field">
            Doctor’s name
            <input
              autoComplete="off"
              maxLength={120}
              value={search.name}
              onChange={(event) => setSearch({ ...search, name: event.target.value })}
            />
          </label>
          <label className="field">
            Registration number
            <input
              autoComplete="off"
              maxLength={80}
              value={search.registration_number}
              onChange={(event) => setSearch({ ...search, registration_number: event.target.value })}
            />
          </label>
          <label className="field">
            State medical council
            <input
              autoComplete="off"
              maxLength={120}
              value={search.council}
              onChange={(event) => setSearch({ ...search, council: event.target.value })}
            />
          </label>
          <div className="doctor-search-actions">
            <Button type="submit" disabled={loading}>
              {loading ? <LoaderCircle className="doctor-spinner" size={16} aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
              {loading ? 'Searching…' : 'Search register'}
            </Button>
          </div>
        </form>
        {error && <p className="form-error doctor-search-message" role="alert">{error}</p>}
        <p className="doctor-verification-notice" role="note">
          Results depend on the configured data source and are not official verification. A missing match does not prove that a doctor is unregistered.
        </p>
      </Card>
      {loading && <p className="loading" role="status">Searching registration records…</p>}
      {results && results.length === 0 && (
        <Card className="doctor-search-message">
          <h2>No matching records found</h2>
          <p>Try another search term. No result is not proof that a doctor is unregistered.</p>
        </Card>
      )}
      {results && results.length > 0 && (
        <section className="doctor-results" aria-label="Registration search results" aria-live="polite">
          <h2>{results.length} {results.length === 1 ? 'record' : 'records'} found</h2>
          {results.map((doctor, index) => (
            <DoctorResult
              key={`${doctor.registration_number || doctor.name || 'record'}-${index}`}
              doctor={doctor}
              index={index}
            />
          ))}
        </section>
      )}
    </>
  )
}
