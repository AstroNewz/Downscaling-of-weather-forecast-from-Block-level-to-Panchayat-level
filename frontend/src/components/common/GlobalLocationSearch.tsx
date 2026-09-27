import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { MapPin, Search, ChevronDown, Check, Building2, Map } from 'lucide-react';

export const GlobalLocationSearch: React.FC = () => {
  const {
    selectedLocationId,
    setSelectedLocationId,
    selectedLocation,
    searchableLocations,
    forecastLoading,
  } = useApp();

  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredLocations = searchableLocations.filter((loc) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      loc.name.toLowerCase().includes(term) ||
      loc.block_name.toLowerCase().includes(term) ||
      loc.district_name.toLowerCase().includes(term) ||
      loc.state_name.toLowerCase().includes(term)
    );
  });

  const handleSelect = (locId: string) => {
    setSelectedLocationId(locId);
    setIsOpen(false);
    setSearchTerm('');
  };

  const currentDisplay = selectedLocation?.name || 'Select Panchayat / Place...';

  return (
    <div className="relative" ref={dropdownRef} id="global-location-selector">
      {/* Trigger Button */}
      <button
        type="button"
        id="location-search-trigger"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-800 hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 shadow-sm transition-all min-w-[220px] max-w-[320px] justify-between"
      >
        <div className="flex items-center gap-2 truncate">
          <MapPin className={`w-3.5 h-3.5 text-blue-600 flex-shrink-0 ${forecastLoading ? 'animate-bounce' : ''}`} />
          <span className="truncate font-semibold text-slate-900">{currentDisplay}</span>
        </div>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 mt-1.5 w-80 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden animate-fade-in">
          {/* Search Box */}
          <div className="p-2 border-b border-slate-100 bg-slate-50/50">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                id="location-search-input"
                type="text"
                autoFocus
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search Panchayat, Block, City..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Location List */}
          <div className="max-h-64 overflow-y-auto p-1.5 divide-y divide-slate-50">
            {filteredLocations.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-500">
                No matching locations found.
              </div>
            ) : (
              filteredLocations.map((loc) => {
                const isSelected = loc.id === selectedLocationId || loc.name === selectedLocation?.name;
                return (
                  <button
                    key={loc.id}
                    type="button"
                    onClick={() => handleSelect(loc.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between text-xs transition-colors ${
                      isSelected
                        ? 'bg-blue-50 text-blue-900 font-semibold'
                        : 'text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-start gap-2 truncate">
                      {loc.type === 'PANCHAYAT' ? (
                        <Building2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                      ) : (
                        <Map className="w-3.5 h-3.5 text-blue-600 mt-0.5 flex-shrink-0" />
                      )}
                      <div className="truncate">
                        <div className="font-medium truncate">{loc.name}</div>
                        <div className="text-[10px] text-slate-500 font-normal">
                          {loc.block_name} • {loc.district_name}, {loc.state_name}
                        </div>
                      </div>
                    </div>
                    {isSelected && <Check className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 ml-2" />}
                  </button>
                );
              })
            )}
          </div>

          {/* Quick Info Footer */}
          <div className="px-3 py-2 bg-slate-50 border-t border-slate-100 text-[10px] text-slate-500 flex justify-between items-center">
            <span>Downscaling at 1-km micro-grid resolution</span>
            <span className="font-mono text-emerald-600 font-medium">LIVE NWP</span>
          </div>
        </div>
      )}
    </div>
  );
};
