import dayjs from 'dayjs'
import advancedFormat from 'dayjs/plugin/advancedFormat'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(advancedFormat)
dayjs.extend(relativeTime)

declare module 'dayjs' {
  interface Dayjs {
    fromNow(withoutSuffix?: boolean): string
  }
}

export default dayjs
