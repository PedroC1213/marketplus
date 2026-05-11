import { motion } from 'framer-motion';
import { AlertTriangle, Users, Calendar } from 'lucide-react';

const campaigns = [
  { id: 1, description: 'Mismo texto "excelente producto" repetido 15 veces en productos distintos', severity: 'Alta', reviewsCount: 15, date: '2025-03-28', status: 'activa' },
  { id: 2, description: 'Ráfaga de reseñas 5 estrellas desde misma IP (190.12.34.56) en 1 hora', severity: 'Media', reviewsCount: 8, date: '2025-03-30', status: 'en revisión' },
  { id: 3, description: 'Cuentas creadas el mismo día publican reseñas positivas idénticas', severity: 'Alta', reviewsCount: 22, date: '2025-04-01', status: 'activa' },
];

export default function CampaignsList() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-4"
    >
      {campaigns.map((camp, idx) => (
        <motion.div
          key={camp.id}
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: idx * 0.1 }}
          className="glass-card p-5 border-l-4 border-l-danger"
        >
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-bold text-lg flex items-center gap-2"><AlertTriangle className="text-danger" size={20} /> Campaña #{camp.id}</h3>
              <p className="text-gray-700 mt-1">{camp.description}</p>
              <div className="flex gap-4 mt-3 text-sm text-gray-500">
                <span className="flex items-center gap-1"><Users size={14} /> {camp.reviewsCount} reseñas</span>
                <span className="flex items-center gap-1"><Calendar size={14} /> {camp.date}</span>
              </div>
            </div>
            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${camp.status === 'activa' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
              {camp.status}
            </span>
          </div>
          <div className="mt-3 flex gap-2">
            <button className="text-primary text-sm hover:underline">Ver reseñas involucradas</button>
            <button className="text-gray-500 text-sm hover:underline">Marcar como revisada</button>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}