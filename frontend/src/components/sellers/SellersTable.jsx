import { useState } from 'react';
import { motion } from 'framer-motion';

const sellers = [
  { id: 1, name: 'TechStore SAS', products: 45, avgRisk: 0.72, riskLevel: 'Alto', flaggedReviews: 12 },
  { id: 2, name: 'Hogar y Más', products: 120, avgRisk: 0.23, riskLevel: 'Bajo', flaggedReviews: 2 },
  { id: 3, name: 'ModaExpress', products: 83, avgRisk: 0.58, riskLevel: 'Medio', flaggedReviews: 7 },
  { id: 4, name: 'ElectroWorld', products: 210, avgRisk: 0.81, riskLevel: 'Alto', flaggedReviews: 24 },
];

export default function SellersTable() {
  const [sort, setSort] = useState('avgRisk');
  const sorted = [...sellers].sort((a, b) => b[sort] - a[sort]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass-card p-4 overflow-x-auto"
    >
      <div className="mb-3 flex justify-end">
        <select onChange={(e) => setSort(e.target.value)} className="border rounded px-2 py-1 text-sm">
          <option value="avgRisk">Ordenar por riesgo</option>
          <option value="flaggedReviews">Ordenar por reseñas marcadas</option>
        </select>
      </div>
      <table className="min-w-full">
        <thead className="bg-gray-50">
          <tr><th>Vendedor</th><th>Productos</th><th>Riesgo promedio</th><th>Reseñas marcadas</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          {sorted.map(s => (
            <tr key={s.id} className="border-b hover:bg-gray-50">
              <td className="py-2 font-medium">{s.name}</td>
              <td>{s.products}</td>
              <td>
                <div className="flex items-center gap-2">
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div className="bg-primary h-2 rounded-full" style={{ width: `${s.avgRisk * 100}%` }}></div>
                  </div>
                  <span>{s.avgRisk.toFixed(2)}</span>
                </div>
              </td>
              <td><Badge level={s.riskLevel.toLowerCase()} /></td>
              <td><a href="#" className="text-primary text-sm hover:underline">Ver detalles</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
}

function Badge({ level }) {
  const classes = { bajo: 'badge-bajo', medio: 'badge-medio', alto: 'badge-alto' };
  return <span className={classes[level]}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>;
}