import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import ChartCard from './ChartCard'
import type { TeacherDeskStudent } from '../types'
import {
  CHART_GRID,
  CHART_SKY,
  CHART_SKY_LIGHT,
  CHART_TICK,
  formatPublishedCoverage,
  formatScore,
} from '../utils'

type SubjectScoreCurveChartProps = {
  students: TeacherDeskStudent[]
  subjectName: string
  passMark: number
  studentsCount?: number
}

type CurvePoint = {
  score: number
  label: string
  count: number
}

const BIN_WIDTH = 5

const buildScoreBins = (students: TeacherDeskStudent[]): CurvePoint[] => {
  const binCount = Math.floor(100 / BIN_WIDTH) + 1
  const bins: CurvePoint[] = Array.from({ length: binCount }, (_, index) => {
    const score = index * BIN_WIDTH
    const end = Math.min(100, score + BIN_WIDTH - 1)
    return {
      score,
      label: score === 100 ? '100' : `${score}–${end}`,
      count: 0,
    }
  })

  for (const student of students) {
    const clamped = Math.max(0, Math.min(100, student.average_score))
    const index = clamped >= 100 ? bins.length - 1 : Math.floor(clamped / BIN_WIDTH)
    bins[index].count += 1
  }

  return bins
}

const SubjectScoreCurveChart = ({
  students,
  subjectName,
  passMark,
  studentsCount,
}: SubjectScoreCurveChartProps) => {
  const data = buildScoreBins(students)
  const total = students.length
  const maxCount = data.reduce((max, point) => Math.max(max, point.count), 0)
  const yMax = Math.max(1, maxCount)
  const coverage = formatPublishedCoverage(total, studentsCount)

  return (
    <ChartCard
      title="Score curve"
      description={
        total > 0
          ? `${coverage} for ${subjectName}, grouped by mark. X is the score; Y is how many students landed there.`
          : studentsCount
            ? `${coverage} for ${subjectName} so far.`
            : `How many students earned each score range in ${subjectName}.`
      }
      info={`Scores are grouped into ${BIN_WIDTH}-mark bands from 0 to 100. The curve shows how many students fall in each band for ${subjectName}. The dashed line is the pass mark (${formatScore(passMark)}%).`}
      empty={total === 0}
      emptyTitle="No published scores yet"
      emptyDescription={
        studentsCount
          ? `${studentsCount} students in class · publish ${subjectName} to see the score curve.`
          : `Publish results for ${subjectName} to see the score curve.`
      }
      bodyClassName="h-80 w-full"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
          <defs>
            <linearGradient id="scoreCurveFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_SKY_LIGHT} stopOpacity={0.45} />
              <stop offset="100%" stopColor={CHART_SKY_LIGHT} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
          <XAxis
            dataKey="score"
            type="number"
            domain={[0, 100]}
            ticks={[0, 20, 40, 60, 80, 100]}
            tick={{ fill: CHART_TICK, fontSize: 12 }}
            axisLine={{ stroke: CHART_GRID }}
            tickLine={false}
            label={{
              value: 'Score',
              position: 'insideBottom',
              offset: -2,
              fill: CHART_TICK,
              fontSize: 11,
            }}
          />
          <YAxis
            allowDecimals={false}
            domain={[0, yMax]}
            tick={{ fill: CHART_TICK, fontSize: 12 }}
            width={36}
            label={{
              value: 'Students',
              angle: -90,
              position: 'insideLeft',
              offset: 8,
              fill: CHART_TICK,
              fontSize: 11,
            }}
          />
          <ReferenceLine
            x={passMark}
            stroke="#94a3b8"
            strokeDasharray="4 4"
            label={{
              value: 'Pass',
              position: 'insideTopRight',
              fill: CHART_TICK,
              fontSize: 11,
            }}
          />
          <Tooltip
            cursor={{ stroke: CHART_GRID, strokeDasharray: '4 4' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const point = payload[0]?.payload as CurvePoint
              return (
                <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
                  <p className="font-medium text-slate-800">Score {point.label}</p>
                  <p className="mt-1 text-slate-700">
                    {point.count} student{point.count === 1 ? '' : 's'}
                  </p>
                </div>
              )
            }}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke={CHART_SKY}
            strokeWidth={2}
            fill="url(#scoreCurveFill)"
            dot={{ r: 2.5, fill: CHART_SKY, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export default SubjectScoreCurveChart
