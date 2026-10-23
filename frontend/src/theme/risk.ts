import type { ExpressionSpecification } from 'maplibre-gl'

import { tokens } from './tokens'
import type { RiskLevel } from '../types'

// One color scale for every risk display: map lines, markers, chips, bars, legend, heatmap.
export const RISK_LEVELS: RiskLevel[] = ['Low', 'Moderate', 'High', 'Severe', 'No Travel']

export const RISK_COLORS: Record<RiskLevel, string> = tokens.color.risk

/** MapLibre expression: a 0-4 score property -> color. */
export const riskColorExpression = (property = 'level_score', fallback: string = tokens.color.map.routeOther) =>
  [
    'match',
    ['get', property],
    0, RISK_COLORS.Low,
    1, RISK_COLORS.Moderate,
    2, RISK_COLORS.High,
    3, RISK_COLORS.Severe,
    4, RISK_COLORS['No Travel'],
    fallback,
  ] as unknown as ExpressionSpecification

export const RISK_COLOR_EXPRESSION = riskColorExpression()
