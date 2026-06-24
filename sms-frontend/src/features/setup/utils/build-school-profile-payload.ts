import type { SchoolProfileFormData } from '../types'

/** Maps form fields to API field names (without the logo file). */
export function toSchoolProfileApiFields(data: SchoolProfileFormData) {
  return {
    name: data.school_name,
    motto: data.motto,
    address: data.address,
    gps_address: data.gps_address,
    box_address: data.po_box ?? '',
    phone_number: data.phone_number,
    phone_number_alt: data.phone_number_alt ?? '',
    email: data.email,
  }
}

/** Builds multipart FormData ready for PATCH/POST to the school profile endpoint. */
export function buildSchoolProfilePayload(
  data: SchoolProfileFormData,
  logoFile?: File | null,
) {
  const payload = new FormData()
  const fields = toSchoolProfileApiFields(data)

  Object.entries(fields).forEach(([key, value]) => {
    payload.append(key, value)
  })

  if (logoFile) {
    payload.append('logo', logoFile)
  }

  return payload
}
