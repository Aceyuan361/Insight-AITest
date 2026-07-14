export type ModuleCategory = 'agent' | 'assets' | 'testing' | 'ai' | 'infra';

export interface NavSpec {
  label: Record<string, string>;
  icon: string;
  show_in_dashboard: boolean;
}

export interface FrontendSpec {
  route: string;
  entry: string;
  nav: NavSpec;
}

export interface ModuleManifest {
  id: string;
  name: Record<string, string>;
  version: string;
  category: ModuleCategory;
  icon: string;
  order: number;
  description: Record<string, string>;
  frontend: FrontendSpec | null;
  default_enabled: boolean;
}
