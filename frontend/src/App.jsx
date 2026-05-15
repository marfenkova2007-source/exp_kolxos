import React, { useState, useEffect } from 'react';
import { ApiService } from './api'; 

const MONTHS = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];

export default function App() {
  const [step, setStep] = useState('start'); 
  const [startMonth, setStartMonth] = useState(0);
  const [endMonth, setEndMonth] = useState(2);
  const [file, setFile] = useState(null);
  const [loadingText, setLoadingText] = useState('Читаем ваше меню...');
  
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('economy');
  const [filterStatus, setFilterStatus] = useState('all');
  const [errorMsg, setErrorMsg] = useState(null);

  // 1. Отправка PDF на бэкенд (Используем api.js)
  const handleAnalyzeMenu = async () => {
    if (!file) return;
    setStep('loading');
    setErrorMsg(null);
    setLoadingText('Отправляем меню на анализ...');

    try {
      // Вызываем функцию из api.js
      const { task_id } = await ApiService.uploadMenuForAnalysis(file, startMonth, endMonth);

      setLoadingText('Нейросеть изучает меню и ищет фермеров...');

      // Опрашиваем сервер каждую секунду
      const pollInterval = setInterval(async () => {
        try {
          // Вызываем функцию проверки статуса из api.js
          const statusData = await ApiService.getTaskStatus(task_id);

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            setData({ products: statusData.result }); 
            setStep('dashboard');
          } else if (statusData.status === 'error') {
            clearInterval(pollInterval);
            setErrorMsg(statusData.error_msg || 'Произошла ошибка при анализе меню');
            setStep('start');
          }
        } catch (pollErr) {
          clearInterval(pollInterval);
          setErrorMsg(pollErr.message);
          setStep('start');
        }
      }, 1000);

    } catch (err) {
      setErrorMsg(err.message);
      setStep('start');
    }
  };

  // 2. Получение базы сезонов без загрузки PDF (Используем api.js)
  const handleShowBase = async () => {
    setStep('loading');
    setErrorMsg(null);
    setLoadingText('Загружаем сезонный календарь...');

    try {
      // Вызываем функцию получения каталога из api.js
      const resultData = await ApiService.getSeasonalDashboard(startMonth, endMonth);
      
      setData({ products: resultData });
      setStep('dashboard');
    } catch (err) {
      setErrorMsg(err.message);
      setStep('start');
    }
  };

  // Фильтрация карточек на дашборде
  const filteredProducts = data?.products?.filter(p => {
    const matchTab = p.recommendation_type === activeTab;
    const matchStatus = filterStatus === 'all' || p.status === filterStatus;
    return matchTab && matchStatus;
  }) || [];


  // Вспомогательная функция для красивых бейджей статуса
  const getStatusBadge = (status) => {
    switch (status) {
      case 'base': return <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-bold">🌿 Базовый</span>;
      case 'premium': return <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs font-bold">💎 Премиум</span>;
      case 'rare': return <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-xs font-bold">⚡ Редкий</span>;
      default: return null;
    }
  };

  return (
    <div className="min-h-screen bg-cover bg-center relative">
      <div
        className="min-h-screen font-sans text-slate-800 pb-10 bg-cover bg-center"
        style={{backgroundImage: "url('../images/start_image.jpg')"
        }}
>

  <div className="absolute inset-0 bg-white/70 backdrop-blur-sm"></div>

  <div className="relative z-10">
      {/* --- ЭКРАН 1: СТАРТ --- */}
      {step === 'start' && (
        <div className="max-w-3xl mx-auto pt-20 px-4">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <h1 className="text-3xl font-bold mb-2">Сезонные продукты</h1>
            <p className="text-slate-500 mb-8">Планируйте закупки и обновляйте меню заранее</p>

            {errorMsg && (
              <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg text-left">
                <strong>Ошибка:</strong> {errorMsg}
              </div>
            )}

            <div className="mb-8 text-left bg-brand-orange p-6 rounded-xl border border-slate-100">
              <label className="block font-semibold mb-4 text-lg">1. Выберите интересующий срок (max: 3 месяца)</label>
              <div className="flex gap-4 items-center">
                <select 
                  className="w-full p-3 rounded-lg border border-slate-300 bg-white outline-none focus:border-brand-green"
                  value={startMonth}
                  onChange={(e) => setStartMonth(Number(e.target.value))}
                >
                  {MONTHS.map((m, i) => <option key={i} value={i}>{m}</option>)}
                </select>
                <span className="text-slate-400">—</span>
                <select 
                  className="w-full p-3 rounded-lg border border-slate-300 bg-white outline-none focus:border-brand-green"
                  value={endMonth}
                  onChange={(e) => setEndMonth(Number(e.target.value))}
                >
                  {MONTHS.map((m, i) => <option key={i} value={i}>{m}</option>)}
                </select>
              </div>
            </div>


            <div className="mb-8 text-left bg-brand-orange p-6 rounded-xl border border-slate-100">
              <label className="block font-semibold mb-4 text-lg">2. Загрузите текущее меню (PDF)</label>
              <div className="border-2 border-dashed border-slate-300 rounded-xl p-10 text-center transition-colors cursor-pointer">
                <input 
                  type="file" 
                  accept=".pdf" 
                  className="hidden" 
                  id="file-upload"
                  onChange={(e) => setFile(e.target.files[0])}
                />
                <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                  <span className="text-4xl mb-3">📄</span>
                  <span className="font-medium text-slate-700">
                    {file ? file.name : "Нажмите, чтобы выбрать PDF-файл"}
                  </span>
                </label>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <button 
                onClick={handleAnalyzeMenu}
                disabled={!file}
                className="flex-1 bg-brand-yellow hover:bg-brand-green text-white font-bold py-4 rounded-xl transition-all text-lg shadow-md"
              >
                Проанализировать меню
              </button>
              
              <button 
                onClick={handleShowBase}
                className="flex-1 border-2 border-brand-yellow text-brand-yellow hover:bg-brand-orange font-bold py-4 rounded-xl disabled:opacity-50 transition-all text-lg"
              >
                Показать сезонные продукты
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>


      {/* --- ЭКРАН 2: ЗАГРУЗКА --- */}
      {step === 'loading' && (
        <div className="h-screen flex flex-col items-center justify-center">
          <div className="w-16 h-16 border-4 border-green-200 border-t-brand-green rounded-full animate-spin mb-6"></div>
          <h2 className="text-2xl font-semibold animate-pulse text-slate-700">{loadingText}</h2>
        </div>
      )}

      {/* --- ЭКРАН 3: ДАШБОРД --- */}
      {step === 'dashboard' && data && (
        <div>
          <div className="sticky top-0 bg-white shadow-md z-50 p-4 border-b border-slate-200">
            <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold">Рекомендации от Своё.Шеф</h2>
                <div className="flex gap-3 mt-2 text-sm">
                  {getStatusBadge('base')}
                  {getStatusBadge('premium')}
                  {getStatusBadge('rare')}
                </div>
              </div>
              
              <select 
                className="p-2 border border-slate-300 rounded-lg outline-none focus:border-brand-green w-full sm:w-auto"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="all">Все статусы</option>
                <option value="base">Только Базовые</option>
                <option value="premium">Только Премиум</option>
                <option value="rare">Только Редкие</option>
              </select>
            </div>
            
            <div className="max-w-6xl mx-auto mt-4 flex gap-4 overflow-x-auto">
              <button 
                onClick={() => setActiveTab('economy')}
                className={`pb-2 px-1 font-semibold border-b-2 transition-colors whitespace-nowrap ${activeTab === 'economy' ? 'border-brand-green text-brand-green' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Оптимизация фудкоста
              </button>
              <button 
                onClick={() => setActiveTab('inspiration')}
                className={`pb-2 px-1 font-semibold border-b-2 transition-colors whitespace-nowrap ${activeTab === 'inspiration' ? 'border-brand-green text-brand-green' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
              >
                Сезонные спешлы
              </button>
            </div>
          </div>

          <div className="max-w-6xl mx-auto p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProducts.map((product) => (
              <div key={product.product_id} className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 hover:shadow-lg transition-all flex flex-col h-full hover:-translate-y-1">
                
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold capitalize leading-tight pr-2 text-slate-800">{product.product_name}</h3>
                  <div className="flex-shrink-0">{getStatusBadge(product.status)}</div>
                </div>


                <div className="mb-4">
                  <span className="text-xs text-slate-500 uppercase font-semibold">Сезонность</span>
                  <div className="flex w-full h-6 mt-1 rounded overflow-hidden border border-slate-200 bg-slate-100">
                    {MONTHS.map((m, i) => {
                      const isSeason = product.season_months.includes(i + 1);
                      const isSelected = i >= startMonth && i <= endMonth;
                      
                      return (
                        <div 
                          key={i} 
                          title={m}
                          className={`flex-1 flex items-center justify-center border-r border-white/50 text-[10px] font-bold
                            ${isSeason ? 'bg-brand-green text-white' : 'text-slate-400'}
                            ${isSelected ? 'ring-2 ring-inset ring-brand-dark scale-110 z-10' : ''}
                          `}
                        >
                          {m.charAt(0)}
                        </div>
                      )
                    })}
                  </div>
                </div>

                {(product.novelty_score !== undefined || product.reason) && (
                  <div className="mb-4 flex-grow flex flex-col gap-2">
                    {product.novelty_score !== undefined && (
                      <div className="inline-flex items-center gap-1 bg-brand-yellow/20 text-yellow-800 w-fit px-2 py-1 rounded text-sm font-bold">
                        🔥 Новизна: {product.novelty_score}%
                      </div>
                    )}
                    {product.reason && (
                      <p className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100 flex-grow">
                        {product.reason}
                      </p>
                    )}
                  </div>
                )}

                <div className="mt-auto pt-4 border-t border-slate-100">
                  <div className="text-sm text-slate-500 mb-3">Фермер: <span className="font-semibold text-slate-700">{product.farmer_name}</span></div>
                  <a 
                    href={product.link}
                    target="_blank"
                    rel="noreferrer" 
                    className="block w-full text-center bg-brand-dark hover:bg-slate-800 text-white font-medium py-3 rounded-xl transition-colors shadow-sm"
                  >
                    Перейти на Своё Родное
                  </a>
                </div>

              </div>
            ))}
            
            {filteredProducts.length === 0 && (
              <div className="col-span-full flex flex-col items-center justify-center py-20 text-slate-500">
                <span className="text-4xl mb-4">🔍</span>
                <p className="text-lg">По выбранным фильтрам продуктов не найдено.</p>
              </div>
            )}
          </div>
          
          <div className="max-w-6xl mx-auto px-6 pb-10 flex justify-center">
             <button 
                onClick={() => { setStep('start'); setFile(null); }}
                className="text-slate-500 hover:text-brand-dark font-medium underline"
             >
               Вернуться к загрузке меню
             </button>
          </div>
        </div>
      )}

    </div>
  );
}
