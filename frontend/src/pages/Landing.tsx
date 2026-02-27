import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Brain, Zap, BarChart3 } from 'lucide-react';
import { Link } from 'react-router-dom';

const Landing: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0F1117] via-[#141821] to-[#0F1117]">
      {/* Hero Section */}
      <section className="min-h-screen flex items-center justify-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center max-w-4xl"
        >
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-6xl md:text-7xl font-bold mb-6"
          >
            <span className="text-gradient">AI-powered</span>
            <br />
            Plant Morphology Analysis
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="text-xl text-gray-400 mb-8 max-w-2xl mx-auto"
          >
            Automatic root, stem and leaf segmentation with precise metric extraction.
            Advanced computer vision for agricultural research.
          </motion.p>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="flex gap-4 justify-center"
          >
            <Link to="/analysis">
              <button className="btn-primary text-lg px-8 py-4 flex items-center gap-2">
                Try Demo
                <ArrowRight size={20} />
              </button>
            </Link>
            <Link to="/dashboard">
              <button className="btn-secondary text-lg px-8 py-4">
                View Dashboard
              </button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6">
        <div className="container">
          <motion.h2
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-4xl font-bold text-center mb-16"
          >
            How It Works
          </motion.h2>
          
          <div className="grid-12">
            {[
              {
                icon: <Zap size={32} />,
                title: 'Upload',
                description: 'Drag & drop your plant images or select files from your device'
              },
              {
                icon: <Brain size={32} />,
                title: 'Segment',
                description: 'AI automatically identifies roots, stems, and leaves with high precision'
              },
              {
                icon: <BarChart3 size={32} />,
                title: 'Measure',
                description: 'Get accurate measurements in millimeters and square millimeters'
              }
            ].map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="col-span-12 md:col-span-4"
              >
                <div className="glass-card p-8 h-full text-center group hover:neon-glow transition-all duration-300">
                  <div className="text-green-400 mb-4 flex justify-center">
                    {step.icon}
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                  <p className="text-gray-400">{step.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology */}
      <section className="py-20 px-6 bg-[#141821]">
        <div className="container">
          <motion.h2
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-4xl font-bold text-center mb-16"
          >
            Technology Stack
          </motion.h2>
          
          <div className="grid-12">
            {[
              {
                title: 'PyTorch',
                description: 'Deep learning framework for segmentation models',
                color: 'blue'
              },
              {
                title: 'Computer Vision',
                description: 'Advanced image processing and analysis',
                color: 'green'
              },
              {
                title: 'FastAPI',
                description: 'High-performance async backend framework',
                color: 'purple'
              },
              {
                title: 'Research-based',
                description: 'Built on latest agricultural research',
                color: 'orange'
              }
            ].map((tech, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="col-span-12 md:col-span-6 lg:col-span-3"
              >
                <div className="glass-card p-6 h-full text-center">
                  <h3 className={`text-xl font-semibold mb-3 ${
                    tech.color === 'green' ? 'text-green-400' :
                    tech.color === 'blue' ? 'text-blue-400' :
                    tech.color === 'purple' ? 'text-purple-400' :
                    'text-orange-400'
                  }`}>
                    {tech.title}
                  </h3>
                  <p className="text-gray-400 text-sm">{tech.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default Landing;
