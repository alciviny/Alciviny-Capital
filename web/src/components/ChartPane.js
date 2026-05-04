"use client";
import { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, LineSeries } from "lightweight-charts";

export default function ChartPane({ id, data, height = 300, isMain = false, visible = true, config = {}, overlays = [], visibleIndicators = {}, indicatorsConfig = {}, syncGroup }) {
  const containerRef = useRef();
  const chartRef = useRef();
  const seriesRef = useRef();
  const overlaySeriesRef = useRef({});

  useEffect(() => {
    if (!visible || !data || data.length === 0) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: height,
      layout: { background: { color: "transparent" }, textColor: "#d1d4dc" },
      grid: { vertLines: { color: "rgba(42, 46, 57, 0.5)" }, horzLines: { color: "rgba(42, 46, 57, 0.5)" } },
      timeScale: { visible: isMain, borderColor: "rgba(197, 203, 206, 0.2)", timeVisible: true },
      rightPriceScale: { borderColor: "rgba(197, 203, 206, 0.2)" },
    });

    if (isMain) {
      seriesRef.current = chart.addSeries(CandlestickSeries, { upColor: "#26a69a", downColor: "#ef5350", borderVisible: false });
      seriesRef.current.setData(data.map(d => ({ ...d, time: d.time / 1000 })));
      overlays.forEach(col => {
        const parentKey = Object.keys(indicatorsConfig).find(k => col.toUpperCase().includes(k.split('_')[0].toUpperCase()));
        const color = indicatorsConfig[parentKey]?.color || '#fbc02d';
        const s = chart.addSeries(LineSeries, { color: col.includes('1.5') ? 'rgba(255,255,255,0.2)' : color, lineWidth: col.includes('1.5') ? 1 : 2 });
        s.setData(data.filter(d => d[col] !== null).map(d => ({ time: d.time / 1000, value: d[col] })));
        overlaySeriesRef.current[col] = s;
      });
    } else {
      seriesRef.current = chart.addSeries(LineSeries, { color: config.color || "#2962FF", lineWidth: 2, title: id.toUpperCase() });
      seriesRef.current.setData(data.filter(d => d[id] !== null).map(d => ({ time: d.time / 1000, value: d[id] })));
      if (config.grid_lines) config.grid_lines.forEach(val => seriesRef.current.createPriceLine({ price: val, color: "rgba(255, 255, 255, 0.1)", lineStyle: 2 }));
    }

    chartRef.current = chart;
    syncGroup.register(id, chart, seriesRef.current);
    const handleResize = () => chart.applyOptions({ width: containerRef.current.clientWidth });
    window.addEventListener("resize", handleResize);
    return () => { window.removeEventListener("resize", handleResize); syncGroup.unregister(id); chart.remove(); };
  }, [data, visible, overlays, config, indicatorsConfig, height, id, isMain, syncGroup]);

  useEffect(() => {
    if (isMain && overlaySeriesRef.current) {
      Object.keys(overlaySeriesRef.current).forEach(col => {
        const parentKey = Object.keys(visibleIndicators).find(name => col.toUpperCase().includes(name.split('_')[0].toUpperCase()));
        overlaySeriesRef.current[col].applyOptions({ visible: parentKey ? visibleIndicators[parentKey] : false });
      });
    }
  }, [visibleIndicators, isMain]);

  if (!visible) return null;
  return <div className="chart-pane" style={{ background: "rgba(20, 24, 33, 0.5)", marginBottom: isMain ? "2px" : "0" }}><div ref={containerRef} /></div>;
}
