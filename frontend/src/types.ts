export type Value = string | boolean | number | string[]
export interface Config { values: Record<string, Value>; extra: string }
export interface Option {
  id: string; group: string; groupLabel: string; flags: string[]; flag: string
  action: string; type: string; choices: string[] | null; default: Value | null
  label: string; description: string; help: string; tool: boolean; file: boolean
  multiline: boolean; repeatable: boolean; dependency: string | null
}
export interface Run {
  id: string; status: string; started: number; ended: number | null
  command: string; message: string; exitCode: number | null; output: string | null
}
export interface Note { title: string; text: string }
export interface ResultFile { root: string; path: string; size: number; modified: number }
export interface Environment {
  sqlmap: string; expectedVersion: string; python: string; pythonPath: string
  terminal: string; platform: string; optional: Record<string, boolean>
}
