import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const useUIStore = create(
  persist(
    (set) => ({
      selectedAsset: "",
      selectedTimeframe: "",
      setSelectedAsset: (asset) => set({ selectedAsset: asset }),
      setSelectedTimeframe: (tf) => set({ selectedTimeframe: tf }),
      indicatorsConfig: {},
      visibleIndicators: {},
      setIndicatorsConfig: (config) => set((state) => {
        const newVisible = { ...state.visibleIndicators };
        Object.keys(config).forEach(k => {
          if (newVisible[k] === undefined) {
            newVisible[k] = config[k].enabled !== false;
          }
        });
        return { indicatorsConfig: config, visibleIndicators: newVisible };
      }),
      toggleIndicator: (name) => set((state) => ({
        visibleIndicators: { ...state.visibleIndicators, [name]: !state.visibleIndicators[name] }
      })),
    }),
    {
      name: 'alciviny-ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        selectedAsset: state.selectedAsset, 
        selectedTimeframe: state.selectedTimeframe,
        visibleIndicators: state.visibleIndicators 
      }),
    }
  )
);
export default useUIStore;
