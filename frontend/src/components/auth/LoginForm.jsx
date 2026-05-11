import { useState } from 'react';
import { motion } from 'framer-motion';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    // Simulación de API (reemplazar con llamada real)
    setTimeout(() => {
      if (email === 'admin@marketplus.com' && password === '123456') {
        localStorage.setItem('token', 'fake-jwt-token');
        window.location.href = '/dashboard';
      } else {
        setError('Credenciales incorrectas. Prueba admin@marketplus.com / 123456');
      }
      setLoading(false);
    }, 800);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass-card w-full max-w-md p-8 mx-4"
    >
      <h2 className="text-2xl font-bold text-center mb-6">Acceso al panel de IA</h2>
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-gray-700 font-medium mb-1">Correo electrónico</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>
        <div className="mb-6">
          <label className="block text-gray-700 font-medium mb-1">Contraseña</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Ingresando...' : 'Iniciar sesión'}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-gray-500">
        Demo: <span className="font-mono">admin@marketplus.com</span> / <span className="font-mono">123456</span>
      </p>
    </motion.div>
  );
}