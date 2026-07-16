import { Icon } from '@iconify/react'

import FeesSetupForm from './components/FeesSetupForm'
import FeesSetupTable from './components/FeesSetupTable'
import Button from '@/components/ui/Button'

const Fees = () => {
  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-lg text-slate-900">Fees Setup (Applies to current term)</h2>
        <div className="flex justify-between gap-2 items-center">
          <p className="text-sm text-slate-500 mt-1">Define the fees structure for your school.</p>

          <p className="flex items-center gap-1 text-blue-500 text-sm">
            <Icon icon="hugeicons:information-circle" className="size-4 " />{' '}
            <span>You can add or edit fees for your school.</span>
          </p>
        </div>
      </div>

      <FeesSetupForm />

      <div className="">
        <h3 className="text-lg mb-2 text-slate-900">Fees Structure Summary</h3>
        <FeesSetupTable />
      </div>

      <Button type="button" variant="outline">
        Proceed to Next Step
      </Button>
    </div>
  )
}

export default Fees
