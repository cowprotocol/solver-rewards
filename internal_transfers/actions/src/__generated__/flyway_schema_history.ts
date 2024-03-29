/**
 * !!! This file is autogenerated do not edit by hand !!!
 *
 * Generated by: @databases/pg-schema-print-types
 * Checksum: sEOFGCV3mwT+RsR7+QUtG+LWbfObYsdw4nUCV5B0CPLnqA/Wt0GEbQJqIfSbkrycquRTKbzVO6Ovrte8yGUUag==
 */

/* eslint-disable */
// tslint:disable

interface FlywaySchemaHistory {
  checksum: number | null;
  description: string;
  execution_time: number;
  installed_by: string;
  /**
   * @default now()
   */
  installed_on: Date;
  installed_rank: number & {
    readonly __brand?: "flyway_schema_history_installed_rank";
  };
  script: string;
  success: boolean;
  type: string;
  version: string | null;
}
export default FlywaySchemaHistory;

interface FlywaySchemaHistory_InsertParameters {
  checksum?: number | null;
  description: string;
  execution_time: number;
  installed_by: string;
  /**
   * @default now()
   */
  installed_on?: Date;
  installed_rank: number & {
    readonly __brand?: "flyway_schema_history_installed_rank";
  };
  script: string;
  success: boolean;
  type: string;
  version?: string | null;
}
export type { FlywaySchemaHistory_InsertParameters };
