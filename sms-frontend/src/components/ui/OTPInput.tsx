import { useRef, type ClipboardEvent, type KeyboardEvent } from 'react'
import { mergeClasses } from '@/utils'

const DEFAULT_LENGTH = 6

export type OTPInputProps = {
  value: string
  onChange: (value: string) => void
  error?: string
  length?: number
  className?: string
}

const OTPInput = ({
  value,
  onChange,
  error,
  length = DEFAULT_LENGTH,
  className,
}: OTPInputProps) => {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  const digits = Array.from({ length }, (_, index) => value[index] ?? '')

  const focusInput = (index: number) => {
    if (index >= 0 && index < length) {
      inputRefs.current[index]?.focus()
      inputRefs.current[index]?.select()
    }
  }

  const handleChange = (index: number, inputValue: string) => {
    const digit = inputValue.replace(/\D/g, '').slice(-1)
    if (!digit) return

    const nextDigits = [...digits]
    nextDigits[index] = digit
    onChange(nextDigits.join('').slice(0, length))

    if (index < length - 1) {
      focusInput(index + 1)
    }
  }

  const handleKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace') {
      event.preventDefault()

      if (digits[index]) {
        const nextDigits = [...digits]
        nextDigits[index] = ''
        onChange(nextDigits.join(''))
        return
      }

      if (index > 0) {
        const nextDigits = [...digits]
        nextDigits[index - 1] = ''
        onChange(nextDigits.join(''))
        focusInput(index - 1)
      }
    }

    if (event.key === 'ArrowLeft' && index > 0) {
      event.preventDefault()
      focusInput(index - 1)
    }

    if (event.key === 'ArrowRight' && index < length - 1) {
      event.preventDefault()
      focusInput(index + 1)
    }
  }

  const handlePaste = (event: ClipboardEvent<HTMLInputElement>) => {
    event.preventDefault()

    const pastedDigits = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, length)
    if (!pastedDigits) return

    onChange(pastedDigits)
    focusInput(Math.min(pastedDigits.length, length) - 1)
  }

  const errorId = 'otp-input-error'

  return (
    <div className={mergeClasses('flex flex-col gap-1.5', className)}>
      <div
        className="flex justify-center items-center gap-2 w-full"
        role="group"
        aria-label="One-time password"
      >
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(element) => {
              inputRefs.current[index] = element
            }}
            type="text"
            inputMode="numeric"
            autoComplete={index === 0 ? 'one-time-code' : 'off'}
            maxLength={1}
            value={digit}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
            className={mergeClasses(
              'lg:size-20 size-16 rounded-lg border border-slate-300 bg-slate-100 text-center text-xl lg:text-2xl font-semibold text-slate-900 outline-none transition',
              'focus:border-slate-400 focus:ring-1 focus:ring-slate-400',
              error && 'border-red-500 focus:border-red-500 focus:ring-red-200/80',
            )}
            onChange={(event) => handleChange(index, event.target.value)}
            onKeyDown={(event) => handleKeyDown(index, event)}
            onPaste={handlePaste}
            onFocus={(event) => event.target.select()}
          />
        ))}
      </div>
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-red-600 text-center">
          {error}
        </p>
      ) : null}
    </div>
  )
}

export default OTPInput
