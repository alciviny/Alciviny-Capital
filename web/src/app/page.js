"use client";
import { useState, useEffect } from "react";
import TradingChart from "../components/TradingChart";
import { ENDPOINTS } from "../config";

export default function Home() {
  const [catalog, setCatalog] = useState({});
  const [selectedAsset, setSelectedAsset] = useState("");
  const [selectedTimeframe, setSelectedTimeframe] = useState("");
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [indicatorsConfig, setIndicatorsConfig] = useState({});
  const [visibleIndicators, setVisibleIndicators] = useState({});

  // 1. Carregar catálogo e config de indicadores
  useEffect(() => {
    // Catálogo
    fetch(ENDPOINTS.CATALOG)
      .then((res) => res.json())
      .then((data) => {
        setCatalog(data.assets);
        const assets = Object.keys(data.assets);
        if (assets.length > 0) {
          const firstAsset = assets[0];
          setSelectedAsset(firstAsset);
          setSelectedTimeframe(data.assets[firstAsset][0]);
        }
      })
      .catch(err => setError("Erro ao conectar com o servidor da API."));

    // Config de Indicadores
    fetch(ENDPOINTS.INDICATORS_CONFIG)
      .then(res => res.json())
      .then(d => {
        const conf = d.indicators || d;
        setIndicatorsConfig(conf);
        // Ativar todos por padrão
        const initialVisible = {};
        Object.keys(conf).forEach(k => {
          if (conf[k].enabled !== false) initialVisible[k] = true;
        });
        setVisibleIndicators(initialVisible);
      })
      .catch(err => console.error("Erro ao carregar configuração de indicadores:", err));
  }, []);

  // 2. Carregar dados quando asset ou timeframe mudarem
  useEffect(() => {
    if (selectedAsset && selectedTimeframe) {
      setLoading(true);
      setError(null);
      fetch(ENDPOINTS.DATA(selectedAsset, selectedTimeframe))
        .then((res) => {
          if (!res.ok) throw new Error(`Falha ao carregar [${selectedAsset}]: ${res.statusText}`);
          return res.json();
        })
        .then((data) => {
          setChartData(data);
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    }
  }, [selectedAsset, selectedTimeframe]);

  const toggleIndicator = (name) => {
    setVisibleIndicators(prev => ({
      ...prev,
      [name]: !prev[name]
    }));
  };

  return (
    <main className="container">
      <header className="glass">
        <div className="brand">
          <h1>AlcivinyEdger</h1>
          <span className="badge">PRO QUANT</span>
        </div>
        
        <div className="controls">
          <div className="select-group">
            <label>Ativo</label>
            <select value={selectedAsset} onChange={(e) => {
              setSelectedAsset(e.target.value);
              setSelectedTimeframe(catalog[e.target.value][0]);
            }}>
              {Object.keys(catalog).map((asset) => (
                <option key={asset} value={asset}>{asset}</option>
              ))}
            </select>
          </div>

          <div className="select-group">
            <label>Timeframe</label>
            <select value={selectedTimeframe} onChange={(e) => setSelectedTimeframe(e.target.value)}>
              {catalog[selectedAsset]?.map((tf) => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="indicator-toggles">
          {Object.keys(indicatorsConfig).map(name => (
            <button 
              key={name}
              className={`toggle-btn ${visibleIndicators[name] ? 'active' : ''}`}
              onClick={() => toggleIndicator(name)}
            >
              {name.toUpperCase().replace('_', ' ')}
            </button>
          ))}
        </div>
      </header>

      <section className="chart-section glass">
        {error ? (
          <div className="error-message">⚠️ {error}</div>
        ) : loading ? (
          <div className="loader">Sincronizando dados...</div>
        ) : chartData.length > 0 ? (
          <TradingChart 
            data={chartData} 
            visibleIndicators={visibleIndicators} 
            indicatorsConfig={indicatorsConfig} 
          />
        ) : (
          <div className="no-data">Nenhum dado disponível para este ativo.</div>
        )}
      </section>
    </main>
  );
}
