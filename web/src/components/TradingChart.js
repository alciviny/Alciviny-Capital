"use client";
import { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, LineSeries } from "lightweight-charts";

export default function TradingChart({ data, visibleIndicators, indicatorsConfig }) {
  const containerRef = useRef();
  const chartsRef = useRef({}); // { main: chart, oscillators: { name: chart } }
  const seriesRef = useRef({}); // { name: series }

  // 1. Inicialização dos Gráficos e Dados
  useEffect(() => {
    if (!data || data.length === 0 || !containerRef.current || !indicatorsConfig) return;

    const cleanup = () => {
      Object.values(chartsRef.current).forEach(c => {
        if (c.remove) c.remove();
        else if (typeof c === 'object') {
           Object.values(c).forEach(sc => sc.remove && sc.remove());
        }
      });
      chartsRef.current = { oscillators: {} };
      seriesRef.current = {};
      if (containerRef.current) containerRef.current.innerHTML = "";
    };

    cleanup();

    const sortedData = [...data].sort((a, b) => a.time - b.time);
    const commonOptions = {
      layout: { background: { color: "#ffffff" }, textColor: "#131722" },
      grid: { vertLines: { color: "rgba(42, 46, 57, 0.06)" }, horzLines: { color: "rgba(42, 46, 57, 0.06)" } },
      timeScale: { borderColor: "#e0e3eb", timeVisible: true },
    };

    // --- PAINEL DE PREÇO (MASTER) ---
    const priceDiv = document.createElement("div");
    priceDiv.style.height = "400px";
    containerRef.current.appendChild(priceDiv);

    const priceChart = createChart(priceDiv, { ...commonOptions, height: 400 });
    const mainSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350"
    });
    mainSeries.setData(sortedData);
    chartsRef.current.main = priceChart;

    // --- INDICADORES (OVERLAYS & SLAVES) ---
    const allColumns = Object.keys(sortedData[0] || {});
    const vwapColumns = allColumns.filter(k => k.toUpperCase().includes('VWAP'));
    
    // Plotar Overlays (VWAPs) - Criar todas, visibilidade controlada depois
    vwapColumns.forEach(col => {
      const isMainVwap = col.length <= 7;
      const overlaySeries = priceChart.addSeries(LineSeries, { 
        color: isMainVwap ? "#ffd60a" : "rgba(103, 113, 128, 0.4)", 
        lineWidth: isMainVwap ? 2 : 1, 
        lineStyle: isMainVwap ? 0 : 2,
        priceLineVisible: false,
        lastValueVisible: isMainVwap,
        title: isMainVwap ? col : "",
        visible: false // Começa oculto até o sync de visibilidade
      });
      overlaySeries.setData(sortedData.filter(d => d[col] != null).map(d => ({ time: d.time, value: d[col] })));
      seriesRef.current[col] = overlaySeries;
    });

    // Plotar Osciladores (Painéis Separados)
    const oscillatorNames = Object.keys(indicatorsConfig).filter(name => !name.toUpperCase().includes('VWAP'));
    
    oscillatorNames.forEach(name => {
      if (!sortedData[0] || !(name in sortedData[0])) return;

      const splitter = document.createElement("div");
      splitter.className = "splitter";
      splitter.innerHTML = '<div class="handle"></div>';
      containerRef.current.appendChild(splitter);

      const indDiv = document.createElement("div");
      indDiv.style.height = "200px";
      indDiv.style.display = "none"; // Começa oculto
      containerRef.current.appendChild(indDiv);

      const indChart = createChart(indDiv, { ...commonOptions, height: 200 });
      const series = indChart.addSeries(LineSeries, {
        color: indicatorsConfig[name].color || "#2962FF",
        lineWidth: 2,
        title: name.toUpperCase()
      });
      series.setData(sortedData.filter(d => d[name] != null).map(d => ({ time: d.time, value: d[name] })));
      
      // Grids dinâmicos baseados na config (ex: IFR)
      const gridLines = indicatorsConfig[name]?.grid_lines || [];
      gridLines.forEach(l => {
        series.createPriceLine({ 
          price: l, 
          color: 'rgba(103, 113, 128, 0.3)', 
          lineStyle: 2,
          title: l.toString() 
        });
      });

      chartsRef.current.oscillators[name] = { chart: indChart, div: indDiv, splitter };
      
      // Sync de tempo
      priceChart.timeScale().subscribeVisibleTimeRangeChange(r => indChart.timeScale().setVisibleRange(r));
    });

    const handleResize = () => {
      const width = containerRef.current?.clientWidth;
      if (!width) return;
      chartsRef.current.main.applyOptions({ width });
      Object.values(chartsRef.current.oscillators).forEach(o => o.chart.applyOptions({ width }));
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      cleanup();
    };
  }, [data, indicatorsConfig]);

  // 2. Efeito de Sincronismo de Visibilidade (SEM RECONSTRUIR)
  useEffect(() => {
    if (!chartsRef.current.main || !indicatorsConfig) return;

    // Atualizar Overlays (VWAPs)
    Object.keys(seriesRef.current).forEach(col => {
      // Encontrar o baseName
      const baseName = Object.keys(indicatorsConfig).find(name => 
        col.toLowerCase().startsWith(name.toLowerCase()) || 
        (name.toLowerCase() === 'vwap_diario' && col.toUpperCase().includes('_D')) ||
        (name.toLowerCase() === 'vwap_semanal' && col.toUpperCase().includes('_W')) ||
        (name.toLowerCase() === 'vwap_mensal' && col.toUpperCase().includes('_M'))
      );
      const isVisible = visibleIndicators[baseName] === true;
      seriesRef.current[col].applyOptions({ visible: isVisible });
    });

    // Atualizar Osciladores (Painéis)
    Object.keys(chartsRef.current.oscillators).forEach(name => {
      const isVisible = visibleIndicators[name] === true;
      const { div, splitter, chart } = chartsRef.current.oscillators[name];
      div.style.display = isVisible ? "block" : "none";
      splitter.style.display = isVisible ? "flex" : "none";
      if (isVisible) chart.timeScale().setVisibleRange(chartsRef.current.main.timeScale().getVisibleRange());
    });

  }, [visibleIndicators, indicatorsConfig]);

  return (
    <div className="multi-pane-wrapper">
      <div ref={containerRef} className="charts-container" />
      <style jsx global>{`
        .multi-pane-wrapper { background: #ffffff; border-radius: 16px; border: 1px solid #e0e3eb; padding: 10px; }
        .splitter { height: 10px; background: #f8f9fa; cursor: ns-resize; display: flex; align-items: center; justify-content: center; margin: 4px 0; border: 1px solid #e0e3eb; }
        .handle { width: 40px; height: 3px; background: #c1c4cd; border-radius: 2px; }
      `}</style>
    </div>
  );
}
