# MarketPlus

Proyecto de manipulación y análisis de reseñas de mercado, dividido en módulos para escalabilidad.

## Estructura del Proyecto

```
marketplus/
├── frontend/          # Aplicación frontend con Astro + React
│   ├── src/
│   │   ├── components/  # Componentes organizados por features
│   │   ├── layouts/     # Layouts de Astro
│   │   ├── pages/       # Páginas de Astro
│   │   ├── styles/      # Estilos globales
│   │   ├── types/       # Definiciones de tipos TypeScript
│   │   ├── hooks/       # Hooks personalizados de React
│   │   ├── services/    # Servicios para API
│   │   └── lib/         # Utilidades y librerías
│   └── package.json
├── backend/            # API backend (por implementar)
├── database/           # Configuración de base de datos (por implementar)
└── ai-model/           # Modelo de IA para análisis (por implementar)
```

## Instalación y Ejecución

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Tecnologías
- **Frontend**: Astro, React, Tailwind CSS, Framer Motion
- **Animaciones**: Framer Motion para componentes, View Transitions de Astro para páginas
- **Gráficos**: Recharts
- **Iconos**: Lucide React

## Próximas Implementaciones
- Backend con API REST
- Base de datos para almacenamiento de reseñas
- Modelo de IA para detección de reseñas fraudulentas