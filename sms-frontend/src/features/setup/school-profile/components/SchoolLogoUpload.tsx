import ImageUpload from '@/components/shared/ImageUpload'

interface SchoolLogoUploadProps {
  logo?: string
  onLogoChange: (_file: File | null) => void
}

const SchoolLogoUpload = ({ logo, onLogoChange }: SchoolLogoUploadProps) => (
  <ImageUpload
    label="School Logo"
    imageUrl={logo}
    onImageChange={onLogoChange}
    previewAlt="School logo preview"
  />
)

export default SchoolLogoUpload
