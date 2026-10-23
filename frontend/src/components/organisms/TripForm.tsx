import { useState, type FormEvent } from 'react'

import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import InputAdornment from '@mui/material/InputAdornment'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'

import { nextHourInput, toLocalInput } from '../../utils/format'
import { IntervalToggle, PlaceField, PresetChips, type IntervalMiles } from '../molecules'
import type { Place, TripRequest } from '../../types'

export interface TripFormProps {
  onSubmit: (request: TripRequest) => void
  isLoading: boolean
}

const DEFAULT_LOAD_LB = '38000'
const MAX_LOAD_LB = 100_000
// Same window as the backend serializer: a few minutes ago still counts as "leave now"
const PAST_GRACE_MS = 15 * 60_000
const MAX_DAYS_AHEAD = 14

type FieldErrors = Partial<Record<'origin' | 'destination' | 'departure' | 'load', string>>

function validate(origin: Place | null, destination: Place | null, departure: string, load: string): FieldErrors {
  const errors: FieldErrors = {}
  const loadLb = Number(load)
  if (!origin) errors.origin = 'Choose a starting point'
  if (!destination) errors.destination = 'Choose a destination'
  if (origin && destination && origin.lat === destination.lat && origin.lon === destination.lon)
    errors.destination = 'Destination must differ from the origin'
  if (!Number.isFinite(loadLb) || loadLb <= 0) errors.load = 'Enter a load above 0 lb'
  else if (loadLb > MAX_LOAD_LB) errors.load = `Maximum ${MAX_LOAD_LB.toLocaleString()} lb`
  const departsAt = new Date(departure).getTime()
  const now = Date.now()
  if (Number.isNaN(departsAt)) errors.departure = 'Choose a date and time'
  else if (departsAt < now - PAST_GRACE_MS) errors.departure = "Departure can't be in the past"
  else if (departsAt > now + MAX_DAYS_AHEAD * 86_400_000)
    errors.departure = `Forecast is available up to ${MAX_DAYS_AHEAD} days ahead`
  return errors
}

export function TripForm({ onSubmit, isLoading }: TripFormProps) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(nextHourInput)
  // Picker floor, fixed at mount on the same grace as validate(); the backend is the final check
  const [minDeparture] = useState(() => toLocalInput(new Date(Date.now() - PAST_GRACE_MS)))
  const [load, setLoad] = useState(DEFAULT_LOAD_LB)
  const [interval, setInterval] = useState<IntervalMiles>(25)
  const [errors, setErrors] = useState<FieldErrors>({})

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const next = validate(origin, destination, departure, load)
    setErrors(next)
    if (Object.keys(next).length || !origin || !destination) return
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: Math.round(Number(load)),
      interval_mi: interval,
    })
  }

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Stack spacing={2}>
        <PlaceField label="Origin" value={origin} onChange={setOrigin} error={errors.origin} />
        <PlaceField label="Destination" value={destination} onChange={setDestination} error={errors.destination} />

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 2, sm: 1.5 }}>
          <TextField
            label="Departure"
            type="datetime-local"
            value={departure}
            onChange={(e) => setDeparture(e.target.value)}
            error={Boolean(errors.departure)}
            helperText={errors.departure}
            slotProps={{
              inputLabel: { shrink: true },
              htmlInput: { min: minDeparture }, // the picker never offers a date validate() rejects
            }}
          />
          <TextField
            label="Load weight"
            value={load}
            onChange={(e) => setLoad(e.target.value.replace(/[^\d]/g, ''))}
            error={Boolean(errors.load)}
            helperText={errors.load}
            sx={{ maxWidth: { sm: 150 } }}
            slotProps={{
              htmlInput: { inputMode: 'numeric' },
              input: { endAdornment: <InputAdornment position="end">lb</InputAdornment> },
            }}
          />
        </Stack>

        <IntervalToggle value={interval} onChange={setInterval} />

        <Button type="submit" variant="contained" size="large" disabled={isLoading}>
          {isLoading ? 'Planning routes…' : 'Plan routes'}
        </Button>

        <PresetChips
          onPick={(preset) => {
            setOrigin(preset.origin)
            setDestination(preset.destination)
            setErrors({})
          }}
        />
      </Stack>
    </Box>
  )
}
