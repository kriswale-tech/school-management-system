import logo from '@/assets/images/logo.svg'

type AppLogoProps = {
  /** Width in pixels (default: 140). */
  widthPx?: number
  className?: string
}

const AppLogo = ({ widthPx = 140, className }: AppLogoProps) => {
  return (
    <div className={className} style={{ width: `${widthPx}px` }}>
      <img src={logo} alt="logo" className="h-auto w-full" />
    </div>
  )
}

export default AppLogo
