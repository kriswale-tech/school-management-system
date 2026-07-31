import { z } from 'zod'

const ghanaPhoneSchema = z
  .string()
  .min(1, { message: 'Primary phone is required' })
  .regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana phone number')

export const basicDetailsSchema = z.object({
  first_name: z.string().min(1, { message: 'First name is required' }),
  last_name: z.string().min(1, { message: 'Last name is required' }),
  other_names: z.string(),
  gender: z.enum(['male', 'female', 'other'], {
    message: 'Gender is required',
  }),
  date_of_birth: z.string().min(1, { message: 'Date of birth is required' }),
  admission_date: z.string().min(1, { message: 'Admission date is required' }),
})

const relationshipSchema = z.enum(
  [
    'father',
    'mother',
    'guardian',
    'other',
    'uncle',
    'aunt',
    'cousin',
    'sibling',
    'grandparent',
  ],
  { message: 'Relationship is required' },
)

export const guardianItemSchema = z.discriminatedUnion('mode', [
  z.object({
    mode: z.literal('new'),
    parent_id: z.string(),
    name: z.string().min(1, { message: 'Guardian name is required' }),
    phone_number: ghanaPhoneSchema,
    email: z
      .string()
      .refine((value) => !value || z.string().email().safeParse(value).success, {
        message: 'Invalid email address',
      }),
    relationship: relationshipSchema,
  }),
  z.object({
    mode: z.literal('existing'),
    parent_id: z.string().uuid({ message: 'Select an existing parent' }),
    name: z.string(),
    phone_number: z.string(),
    email: z.string(),
    relationship: relationshipSchema,
  }),
])

export const guardianInfoSchema = z.object({
  guardians: z.array(guardianItemSchema).min(1, { message: 'Add at least one guardian' }),
})

export const classPlacementSchema = z.object({
  stream_id: z.string().uuid({ message: 'Select a class' }),
  is_new_student: z.boolean({ message: 'Select student status' }),
})

export const studentFormSchema = basicDetailsSchema
  .merge(guardianInfoSchema)
  .merge(classPlacementSchema)
