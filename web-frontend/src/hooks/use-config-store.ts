import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { 
  AgentMode, 
  UserPreferences, 
  ReactAgentConfig, 
  CodeActAgentConfig,
  ModelConfig,
  ToolSpecificConfig,
  VerbosityLevel,
  ExecutorType,
  RerankerType
} from '@/types/config';

interface ConfigStore {
  // Current configuration state
  preferences: UserPreferences;
  
  // Actions for updating configuration
  setAgentMode: (mode: AgentMode) => void;
  updateAgentConfig: (config: Partial<ReactAgentConfig & CodeActAgentConfig>) => void;
  updateModelConfig: (config: Partial<ModelConfig>) => void;
  updateToolConfig: (config: Partial<ToolSpecificConfig>) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setAutoSave: (autoSave: boolean) => void;
  
  // Reset to defaults
  resetToDefaults: () => void;
  resetAgentConfig: () => void;
  
  // Getters for current agent-specific config
  getCurrentAgentConfig: () => ReactAgentConfig | CodeActAgentConfig;
  
  // Validation
  isConfigValid: () => boolean;
}

// Default configurations
const defaultReactConfig: ReactAgentConfig = {
  max_steps: 25,
  planning_interval: 7,
  verbosity_level: 2,
};

const defaultCodeActConfig: CodeActAgentConfig = {
  executor_type: 'local',
  max_steps: 25,
  planning_interval: 5,
  verbosity_level: 2,
  executor_kwargs: {},
  additional_authorized_imports: [],
};

const defaultModelConfig: ModelConfig = {
  orchestrator_id: 'gemini/gemini-2.5-pro-preview-05-06',
  search_id: 'anthropic/claude-sonnet-4-20250514',
  reranker_type: 'jina-reranker-m0',
};

const defaultToolConfig: ToolSpecificConfig = {
  rerank_texts: {
    default_model: 'jina-reranker-m0',
  },
  search_links: {
    num_results: 10,
    location: 'us',
  },
  read_url: {
    reader_model: 'readerlm-v2',
  },
  chunk_text: {
    chunk_size: 150,
    chunk_overlap: 50,
  },
};

const defaultPreferences: UserPreferences = {
  selectedAgentMode: 'codact',
  agentConfig: { ...defaultCodeActConfig },
  modelConfig: { ...defaultModelConfig },
  toolConfig: { ...defaultToolConfig },
  theme: 'system',
  autoSave: true,
};

export const useConfigStore = create<ConfigStore>()(
  persist(
    (set, get) => ({
      preferences: defaultPreferences,
      
      setAgentMode: (mode: AgentMode) => {
        set((state) => {
          const newAgentConfig = mode === 'react' 
            ? { ...defaultReactConfig }
            : { ...defaultCodeActConfig };
          
          return {
            preferences: {
              ...state.preferences,
              selectedAgentMode: mode,
              agentConfig: newAgentConfig,
            },
          };
        });
      },
      
      updateAgentConfig: (config) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            agentConfig: { ...state.preferences.agentConfig, ...config },
          },
        }));
      },
      
      updateModelConfig: (config) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            modelConfig: { ...state.preferences.modelConfig, ...config },
          },
        }));
      },
      
      updateToolConfig: (config) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            toolConfig: { ...state.preferences.toolConfig, ...config },
          },
        }));
      },
      
      setTheme: (theme) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            theme,
          },
        }));
      },
      
      setAutoSave: (autoSave) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            autoSave,
          },
        }));
      },
      
      resetToDefaults: () => {
        set({ preferences: { ...defaultPreferences } });
      },
      
      resetAgentConfig: () => {
        const { selectedAgentMode } = get().preferences;
        const defaultConfig = selectedAgentMode === 'react' 
          ? { ...defaultReactConfig }
          : { ...defaultCodeActConfig };
        
        set((state) => ({
          preferences: {
            ...state.preferences,
            agentConfig: defaultConfig,
          },
        }));
      },
      
      getCurrentAgentConfig: () => {
        const { preferences } = get();
        return preferences.agentConfig as ReactAgentConfig | CodeActAgentConfig;
      },
      
      isConfigValid: () => {
        const { preferences } = get();
        const { agentConfig, modelConfig } = preferences;
        
        // Basic validation
        if (!agentConfig.max_steps || agentConfig.max_steps < 1 || agentConfig.max_steps > 100) {
          return false;
        }
        
        if (!agentConfig.planning_interval || agentConfig.planning_interval < 1) {
          return false;
        }
        
        if (!modelConfig.orchestrator_id || !modelConfig.search_id) {
          return false;
        }
        
        return true;
      },
    }),
    {
      name: 'deepsearch-config',
      version: 1,
    }
  )
);


