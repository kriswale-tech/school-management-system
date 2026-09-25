import type { ReactNode } from 'react'

type WelcomeBannerProps = {
  firstName: string
  children?: ReactNode
}

const WelcomeBanner = ({ firstName, children }: WelcomeBannerProps) => {
  return (
    <section className="-mx-6 -mt-6">
      <div className="relative bg-[#0B2E4F] px-6 pt-8 pb-28 sm:pt-10 sm:pb-32">
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: "url('/images/dashboard-banner.png')" }}
          aria-hidden
        />
        <div className="relative">
          <p className="text-white text-lg sm:text-xl font-semibold">
            Welcome Back{firstName ? `, ${firstName}` : ','}
          </p>
          <p className="text-slate-200 text-sm mt-1">Here&apos;s your updated overview.</p>
        </div>
      </div>

      {children ? (
        <div className="relative z-10 -mt-14 px-6 sm:-mt-16">{children}</div>
      ) : null}
    </section>
  )
}

export default WelcomeBanner
