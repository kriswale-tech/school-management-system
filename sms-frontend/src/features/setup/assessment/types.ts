export interface GradeBand {
    id: string;
    grade: string;
    min_score: number;
    max_score: number;
    remark: string;
  }
  
  export interface GradeTemplate {
    grade: string;
    min_score: number;
    max_score: number;
    remark: string;
  }
  
  export interface GradeTemplates {
    letter: GradeTemplate[];
    numerical: GradeTemplate[];
  }
  
  export type ResultType = "position" | "grade" | "grade_and_position";
  export type GradeType = "letter" | "numerical";
  
  export interface LevelConfig {
    id: string;
    continuous_assessment_weight: string;
    exam_weight: string;
    result_type: ResultType;
    grade_type: GradeType;
    grade_bands: GradeBand[];
  }

  export interface LevelConfigPayload {
    continuous_assessment_weight: number;
    exam_weight: number;
    result_type: ResultType;
    grade_type: GradeType;
    grade_bands: GradeBand[];
  }
  
  export interface Level {
    level_id: string;
    level_name: string;
    level_order: number;
    config: LevelConfig | null;
  }
  
  export interface AssessmentConfigResponse {
    grade_templates: GradeTemplates;
    levels: Level[];
  }