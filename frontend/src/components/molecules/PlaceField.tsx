import { useId, useMemo, useState } from 'react'

import Box from '@mui/material/Box'
import FormHelperText from '@mui/material/FormHelperText'
import { useTheme, type Theme } from '@mui/material/styles'
import Select, { type StylesConfig } from 'react-select'

import { MIN_QUERY_LENGTH, useGeocode } from '../../api'
import { FieldLabel } from '../atoms'
import type { Place } from '../../types'

export interface PlaceFieldProps {
  label: string
  value: Place | null
  onChange: (place: Place | null) => void
  error?: string
}

/** React Select styled from the MUI theme so it sits next to MUI text fields. */
function selectStyles(theme: Theme, hasError: boolean): StylesConfig<Place, false> {
  const { palette, shape, typography, shadows, zIndex } = theme
  const restingBorder = hasError ? palette.error.main : palette.divider
  const font = { fontFamily: typography.fontFamily, fontSize: typography.body2.fontSize }
  return {
    control: (base, state) => ({
      ...base,
      ...font,
      minHeight: 40,
      borderRadius: shape.borderRadius,
      borderColor: state.isFocused ? palette.primary.main : restingBorder,
      boxShadow: state.isFocused ? `0 0 0 1px ${palette.primary.main}` : 'none',
      backgroundColor: palette.background.paper,
      '&:hover': { borderColor: state.isFocused ? palette.primary.main : palette.text.primary },
    }),
    menu: (base) => ({ ...base, ...font, zIndex: zIndex.modal, borderRadius: shape.borderRadius, boxShadow: shadows[8], overflow: 'hidden' }),
    option: (base, state) => ({
      ...base,
      color: palette.text.primary,
      backgroundColor: state.isSelected ? palette.action.selected : state.isFocused ? palette.action.hover : 'transparent',
      '&:active': { backgroundColor: palette.action.selected },
    }),
    placeholder: (base) => ({ ...base, color: palette.text.secondary }),
    singleValue: (base) => ({ ...base, color: palette.text.primary }),
    input: (base) => ({ ...base, color: palette.text.primary }),
    indicatorSeparator: () => ({ display: 'none' }),
    dropdownIndicator: (base) => ({ ...base, color: palette.text.secondary }),
    clearIndicator: (base) => ({ ...base, color: palette.text.secondary }),
  }
}

/** City or address search backed by /api/geocode, with debounced suggestions. */
export function PlaceField({ label, value, onChange, error }: PlaceFieldProps) {
  const theme = useTheme()
  const inputId = useId()
  const [text, setText] = useState('')
  const { data, isFetching } = useGeocode(text)
  // Suggestions belong to the current text only; after a pick or blur the query is reset below
  const options = text.trim().length >= MIN_QUERY_LENGTH ? (data ?? []) : []
  const styles = useMemo(() => selectStyles(theme, Boolean(error)), [theme, error])

  return (
    <Box>
      <FieldLabel htmlFor={inputId} hasError={Boolean(error)}>
        {label}
      </FieldLabel>
      <Select<Place, false>
        inputId={inputId}
        value={value}
        onChange={onChange}
        onInputChange={(next, meta) => {
          if (meta.action === 'input-change') setText(next)
          else setText('') // set-value, input-blur, menu-close: react-select clears its input, so do we
        }}
        options={options}
        getOptionLabel={(place) => place.name}
        getOptionValue={(place) => `${place.lat},${place.lon}`}
        filterOption={null} // the server already filtered
        isLoading={isFetching}
        isClearable
        placeholder="City or address"
        noOptionsMessage={({ inputValue }) =>
          inputValue.trim().length < MIN_QUERY_LENGTH ? 'Type a city or address' : 'No matches'
        }
        styles={styles}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId}-error` : undefined}
      />
      {error && (
        <FormHelperText id={`${inputId}-error`} error sx={{ mx: 0 }}>
          {error}
        </FormHelperText>
      )}
    </Box>
  )
}
