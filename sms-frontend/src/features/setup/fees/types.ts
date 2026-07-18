export type FeeStructureStatus = 'draft' | 'published' | 'applied' | 'carried_forward';

export type AppliesToType = 'level' | 'class' | 'school';

export type StudentType = 'new_student' | 'continuing_student' | 'all_students';

export interface FeeStructure {
    id: string;
    name: string;
    status: FeeStructureStatus;
    status_display: string;
    is_editable: boolean;
    is_locked: boolean;
    term_id: string;
    term_name: string;
    academic_year: string;
  }
  
  export interface FeeItem {
    id: string;
    name: string;
    amount: string; 
    description: string;
    applies_to_type: AppliesToType;
    applies_to_type_display: string;
    applies_to_id: string;
    applies_to_name: string;
    student_type: StudentType;
    student_type_display: string;
  }
  
  export interface FeeStructureResponse {
    fee_structure: FeeStructure;
    fee_items: FeeItem[];
  }

  export interface FeeItemFormValues {
    name: string;
    amount: string; // decimal number
    description: string; //empty string
    applies_to_type: AppliesToType;
    applies_to_id: string | null; // null for school
    student_type: StudentType;
  }
  