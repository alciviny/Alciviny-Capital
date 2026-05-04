"use client";
import { useEffect, useRef, useMemo } from "react";
import useUIStore from "../store/useUIStore";
import ChartPane from "./ChartPane";

export default function TradingChart({ data }) {
  const { visibleIndicators, indicatorsConfig } = useUIStore();
  const syncRef = useRef({
    charts: new Map(),
    register(id, chart, series) {
      this.charts.set(id, { chart, series });
      chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
        this.charts.forEach((c, otherId) => { if (otherId !== id) c.chart.timeScale().setVisibleRange(range); });
      });
      chart.subscribeCrosshairMove((param) => {
        this.charts.forEach((c, otherId) => {
          if (otherId !== id) {
            if (!param.time) c.chart.clearCrosshairPosition();
            else c.chart.setCrosshairPosition(param.price || 0, param.time, c.series);
          }
        });
      });
    },
    unregister(id) { this.charts.delete(id); }
  });

  const { overlays, oscillators } = useMemo(() => {
    const list = Object.keys(indicatorsConfig);
    const os = list.filter(name => indicatorsConfig[name]?.plot_type === 'oscillator');
    const ov_keys = list.filter(name => indicatorsConfig[name]?.plot_type === 'overlay');
    const dataCols = data[0] ? Object.keys(data[0]) : [];
    const vwapCols = dataCols.filter(col => ov_keys.some(key => col.toLowerCase().startsWith(key.split('_')[0].toLowerCase())));
    return { overlays: vwapCols, oscillators: os };
  }, [indicatorsConfig, data]);

  if (!data || data.length === 0) return null;
  return (
    <div className="trading-chart-container" style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <ChartPane id="main" isMain={true} height={450} data={data} overlays={overlays} visibleIndicators={visibleIndicators} indicatorsConfig={indicatorsConfig} syncGroup={syncRef.current} />
      {oscillators.map(name => (
        <ChartPane key={name} id={name} visible={visibleIndicators[name]} data={data} config={indicatorsConfig[name]} syncGroup={syncRef.current} />
      ))}
    </div>
  );
}
