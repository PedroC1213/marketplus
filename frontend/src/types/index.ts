// Definiciones de tipos para el proyecto MarketPlus

export interface Review {
  id: number;
  product: string;
  rating: number;
  text: string;
  risk: 'Bajo' | 'Medio' | 'Alto';
  date: string;
  user: string;
}

export interface Alert {
  id: number;
  product: string;
  risk: 'Bajo' | 'Medio' | 'Alto';
  reason: string;
  time: string;
}

export interface Campaign {
  id: number;
  name: string;
  status: 'Activa' | 'Pausada' | 'Completada';
  reviews: number;
  riskLevel: 'Bajo' | 'Medio' | 'Alto';
}

export interface Seller {
  id: number;
  name: string;
  rating: number;
  reviews: number;
  risk: 'Bajo' | 'Medio' | 'Alto';
}