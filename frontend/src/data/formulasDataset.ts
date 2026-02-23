export interface DatasetEntry {
  id: number;
  name: string;
  formula: string;
  description: string;
  category: string;
  subject: string;
}

export const formulasDataset: DatasetEntry[] = [
  {
    "id": 1,
    "name": "Newton's First Law of Motion",
    "formula": "F = 0 → v = constant",
    "description": "An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an unbalanced force.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 2,
    "name": "Newton's Second Law of Motion",
    "formula": "F = ma",
    "description": "The acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 3,
    "name": "Newton's Third Law of Motion",
    "formula": "F₁₂ = -F₂₁",
    "description": "For every action, there is an equal and opposite reaction.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 4,
    "name": "Law of Universal Gravitation",
    "formula": "F = G(m₁m₂)/r²",
    "description": "Every particle attracts every other particle with a force proportional to the product of their masses and inversely proportional to the square of the distance between them.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 5,
    "name": "Conservation of Energy",
    "formula": "E_total = constant",
    "description": "Energy cannot be created or destroyed, only transformed from one form to another.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 6,
    "name": "Conservation of Momentum",
    "formula": "Σp_initial = Σp_final",
    "description": "The total momentum of a closed system remains constant if no external forces act on it.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 7,
    "name": "Ohm's Law",
    "formula": "V = IR",
    "description": "The voltage across a conductor is directly proportional to the current flowing through it, with resistance as the constant of proportionality.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 8,
    "name": "Coulomb's Law",
    "formula": "F = k(q₁q₂)/r²",
    "description": "The force between two point charges is directly proportional to the product of their charges and inversely proportional to the square of the distance between them.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 9,
    "name": "Faraday's Law of Electromagnetic Induction",
    "formula": "ε = -dΦ/dt",
    "description": "The induced electromotive force in any closed circuit is equal to the negative of the time rate of change of the magnetic flux through the circuit.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 10,
    "name": "Lenz's Law",
    "formula": "ε = -dΦ/dt",
    "description": "The direction of induced current is such that it opposes the change causing it.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 11,
    "name": "Einstein's Mass-Energy Equivalence",
    "formula": "E = mc²",
    "description": "Energy and mass are equivalent and can be converted into each other, where c is the speed of light.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 12,
    "name": "Planck's Law",
    "formula": "E = hf",
    "description": "The energy of a photon is proportional to its frequency, where h is Planck's constant.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 13,
    "name": "Heisenberg Uncertainty Principle",
    "formula": "Δx·Δp ≥ ħ/2",
    "description": "It is impossible to simultaneously know the exact position and momentum of a particle with perfect accuracy.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 14,
    "name": "Pauli Exclusion Principle",
    "formula": "No two identical fermions can occupy the same quantum state",
    "description": "No two electrons in an atom can have the same set of four quantum numbers.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 15,
    "name": "Schrödinger Equation",
    "formula": "iħ(∂ψ/∂t) = Ĥψ",
    "description": "The fundamental equation of quantum mechanics describing how quantum states evolve over time.",
    "category": "Equation",
    "subject": "Physics"
  },
  {
    "id": 16,
    "name": "Maxwell's Equations",
    "formula": "∇·E = ρ/ε₀, ∇×E = -∂B/∂t, ∇·B = 0, ∇×B = μ₀J + μ₀ε₀(∂E/∂t)",
    "description": "Four fundamental equations describing how electric and magnetic fields are generated and altered by charges and currents.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 17,
    "name": "Boyle's Law",
    "formula": "PV = constant (at constant T)",
    "description": "The pressure of a gas is inversely proportional to its volume at constant temperature.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 18,
    "name": "Charles's Law",
    "formula": "V/T = constant (at constant P)",
    "description": "The volume of a gas is directly proportional to its absolute temperature at constant pressure.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 19,
    "name": "Ideal Gas Law",
    "formula": "PV = nRT",
    "description": "The relationship between pressure, volume, temperature, and number of moles of an ideal gas.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 20,
    "name": "First Law of Thermodynamics",
    "formula": "ΔU = Q - W",
    "description": "The change in internal energy of a system equals the heat added to the system minus the work done by the system.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 21,
    "name": "Second Law of Thermodynamics",
    "formula": "ΔS ≥ 0 (for isolated systems)",
    "description": "The total entropy of an isolated system can never decrease over time.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 22,
    "name": "Kinetic Energy",
    "formula": "KE = (1/2)mv²",
    "description": "The energy possessed by an object due to its motion.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 23,
    "name": "Potential Energy (Gravitational)",
    "formula": "PE = mgh",
    "description": "The energy stored in an object due to its position in a gravitational field.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 24,
    "name": "Work-Energy Theorem",
    "formula": "W = ΔKE",
    "description": "The work done on an object equals the change in its kinetic energy.",
    "category": "Theorem",
    "subject": "Physics"
  },
  {
    "id": 25,
    "name": "Power",
    "formula": "P = W/t = Fv",
    "description": "The rate at which work is done or energy is transferred.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 26,
    "name": "Wave Equation",
    "formula": "v = fλ",
    "description": "The speed of a wave equals its frequency multiplied by its wavelength.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 27,
    "name": "Snell's Law",
    "formula": "n₁sin(θ₁) = n₂sin(θ₂)",
    "description": "The relationship between the angles of incidence and refraction when light passes through different media.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 28,
    "name": "Doppler Effect",
    "formula": "f' = f(v ± v₀)/(v ∓ vₛ)",
    "description": "The change in frequency of a wave in relation to an observer moving relative to the wave source.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 29,
    "name": "Einstein's Special Relativity - Time Dilation",
    "formula": "t = t₀/√(1 - v²/c²)",
    "description": "Time passes more slowly for objects moving at high speeds relative to an observer.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 30,
    "name": "Einstein's Special Relativity - Length Contraction",
    "formula": "L = L₀√(1 - v²/c²)",
    "description": "Objects appear shorter in the direction of motion when moving at high speeds.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 31,
    "name": "Photoelectric Effect",
    "formula": "KE_max = hf - φ",
    "description": "Electrons are emitted from a material when light of sufficient frequency strikes it.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 32,
    "name": "De Broglie Wavelength",
    "formula": "λ = h/p = h/(mv)",
    "description": "All matter exhibits wave-like properties, with wavelength inversely proportional to momentum.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 33,
    "name": "Rutherford Scattering",
    "formula": "F = k(Ze)(2e)/(r²)",
    "description": "The scattering of alpha particles by atomic nuclei, leading to the discovery of the atomic nucleus.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 34,
    "name": "Blackbody Radiation",
    "formula": "E = σT⁴",
    "description": "The total energy radiated per unit surface area of a blackbody is proportional to the fourth power of its temperature.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 35,
    "name": "Bernoulli's Principle",
    "formula": "P + (1/2)ρv² + ρgh = constant",
    "description": "In a flowing fluid, an increase in speed occurs simultaneously with a decrease in pressure.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 36,
    "name": "Archimedes' Principle",
    "formula": "F_buoyant = ρ_fluid × V_displaced × g",
    "description": "The upward buoyant force on an object immersed in a fluid equals the weight of the fluid displaced.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 37,
    "name": "Pascal's Principle",
    "formula": "F₁/A₁ = F₂/A₂",
    "description": "Pressure applied to a confined fluid is transmitted undiminished to all parts of the fluid.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 38,
    "name": "Hooke's Law",
    "formula": "F = -kx",
    "description": "The force needed to extend or compress a spring is proportional to the distance it is stretched or compressed.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 39,
    "name": "Centripetal Force",
    "formula": "F = mv²/r",
    "description": "The force required to keep an object moving in a circular path.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 40,
    "name": "Torque",
    "formula": "τ = r × F = rFsin(θ)",
    "description": "The rotational equivalent of force, causing angular acceleration.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 41,
    "name": "Angular Momentum",
    "formula": "L = r × p = Iω",
    "description": "The rotational equivalent of linear momentum, conserved in closed systems.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 42,
    "name": "Moment of Inertia",
    "formula": "I = Σmr²",
    "description": "The resistance of an object to rotational motion, depending on mass distribution.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 43,
    "name": "Angular Velocity",
    "formula": "ω = dθ/dt",
    "description": "The rate of change of angular displacement with respect to time.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 44,
    "name": "Angular Acceleration",
    "formula": "α = dω/dt",
    "description": "The rate of change of angular velocity with respect to time.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 45,
    "name": "Rotational Kinetic Energy",
    "formula": "KE_rot = (1/2)Iω²",
    "description": "The kinetic energy due to rotational motion of a rigid body.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 46,
    "name": "Simple Harmonic Motion",
    "formula": "x(t) = A cos(ωt + φ)",
    "description": "Periodic motion where restoring force is proportional to displacement.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 47,
    "name": "Period of Simple Pendulum",
    "formula": "T = 2π√(L/g)",
    "description": "The time period of a simple pendulum depends only on length and gravitational acceleration.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 48,
    "name": "Period of Spring-Mass System",
    "formula": "T = 2π√(m/k)",
    "description": "The period of oscillation for a mass-spring system depends on mass and spring constant.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 49,
    "name": "Electric Field",
    "formula": "E = F/q = kQ/r²",
    "description": "The force per unit charge experienced by a test charge in an electric field.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 50,
    "name": "Electric Potential",
    "formula": "V = kQ/r",
    "description": "The electric potential energy per unit charge at a point in space.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 51,
    "name": "Electric Potential Energy",
    "formula": "U = qV = k(q₁q₂)/r",
    "description": "The energy stored in a system of charges due to their positions.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 52,
    "name": "Capacitance",
    "formula": "C = Q/V",
    "description": "The ability of a capacitor to store charge per unit voltage.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 53,
    "name": "Energy Stored in Capacitor",
    "formula": "U = (1/2)CV² = (1/2)Q²/C",
    "description": "The energy stored in a charged capacitor.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 54,
    "name": "Magnetic Field (Straight Wire)",
    "formula": "B = μ₀I/(2πr)",
    "description": "The magnetic field around a straight current-carrying wire.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 55,
    "name": "Magnetic Force on Moving Charge",
    "formula": "F = q(v × B)",
    "description": "The force experienced by a moving charge in a magnetic field.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 56,
    "name": "Magnetic Force on Current-Carrying Wire",
    "formula": "F = IL × B",
    "description": "The force on a current-carrying wire in a magnetic field.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 57,
    "name": "Magnetic Flux",
    "formula": "Φ = B·A = BAcos(θ)",
    "description": "The measure of magnetic field passing through a surface.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 58,
    "name": "Self-Inductance",
    "formula": "L = Φ/I",
    "description": "The ratio of magnetic flux to current in a coil, causing opposition to current change.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 59,
    "name": "Energy Stored in Inductor",
    "formula": "U = (1/2)LI²",
    "description": "The energy stored in the magnetic field of an inductor.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 60,
    "name": "AC Circuit - RMS Voltage",
    "formula": "V_rms = V₀/√2",
    "description": "The root mean square voltage in an AC circuit, equivalent to DC voltage producing same power.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 61,
    "name": "AC Circuit - RMS Current",
    "formula": "I_rms = I₀/√2",
    "description": "The root mean square current in an AC circuit.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 62,
    "name": "Resonant Frequency (LC Circuit)",
    "formula": "f = 1/(2π√(LC))",
    "description": "The frequency at which an LC circuit resonates, storing energy between inductor and capacitor.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 63,
    "name": "Refraction Index",
    "formula": "n = c/v",
    "description": "The ratio of speed of light in vacuum to speed in a medium, determining light bending.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 64,
    "name": "Critical Angle",
    "formula": "θ_c = arcsin(n₂/n₁)",
    "description": "The angle of incidence beyond which total internal reflection occurs.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 65,
    "name": "Thin Lens Equation",
    "formula": "1/f = 1/d₀ + 1/dᵢ",
    "description": "Relates focal length to object and image distances for thin lenses.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 66,
    "name": "Magnification",
    "formula": "m = -dᵢ/d₀ = hᵢ/h₀",
    "description": "The ratio of image height to object height, or negative ratio of image to object distance.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 67,
    "name": "Double-Slit Interference",
    "formula": "d sin(θ) = mλ",
    "description": "The condition for constructive interference in double-slit experiment.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 68,
    "name": "Single-Slit Diffraction",
    "formula": "a sin(θ) = mλ",
    "description": "The condition for destructive interference in single-slit diffraction.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 69,
    "name": "Bragg's Law",
    "formula": "nλ = 2d sin(θ)",
    "description": "The condition for constructive interference in X-ray diffraction from crystal planes.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 70,
    "name": "Stefan-Boltzmann Law",
    "formula": "P = σAT⁴",
    "description": "The total power radiated per unit area by a blackbody is proportional to the fourth power of temperature.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 71,
    "name": "Wien's Displacement Law",
    "formula": "λ_max T = b",
    "description": "The wavelength at which blackbody radiation peaks is inversely proportional to temperature.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 72,
    "name": "Compton Scattering",
    "formula": "Δλ = (h/(m_e c))(1 - cos(θ))",
    "description": "The change in wavelength when X-rays scatter off electrons, demonstrating particle nature of light.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 73,
    "name": "Rydberg Constant",
    "formula": "R_H = 1.097 × 10⁷ m⁻¹",
    "description": "The constant in the Rydberg formula for hydrogen spectral lines.",
    "category": "Constant",
    "subject": "Physics"
  },
  {
    "id": 74,
    "name": "Bohr Radius",
    "formula": "a₀ = 5.29 × 10⁻¹¹ m",
    "description": "The most probable distance between electron and nucleus in hydrogen atom ground state.",
    "category": "Constant",
    "subject": "Physics"
  },
  {
    "id": 75,
    "name": "Fine Structure Constant",
    "formula": "α = e²/(4πε₀ħc) ≈ 1/137",
    "description": "A dimensionless constant characterizing the strength of electromagnetic interaction.",
    "category": "Constant",
    "subject": "Physics"
  },
  {
    "id": 76,
    "name": "Schrödinger Equation (Time-Independent)",
    "formula": "Ĥψ = Eψ",
    "description": "The time-independent form of Schrödinger equation for stationary states.",
    "category": "Equation",
    "subject": "Physics"
  },
  {
    "id": 77,
    "name": "Wave Function Normalization",
    "formula": "∫|ψ|² dV = 1",
    "description": "The probability density integrated over all space must equal one.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 78,
    "name": "Expectation Value",
    "formula": "<A> = ∫ψ*Âψ dV",
    "description": "The average value of a physical quantity in quantum mechanics.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 79,
    "name": "Einstein's General Relativity Field Equations",
    "formula": "G_μν = (8πG/c⁴)T_μν",
    "description": "The fundamental equations describing how matter and energy curve spacetime.",
    "category": "Equation",
    "subject": "Physics"
  },
  {
    "id": 80,
    "name": "Schwarzschild Radius",
    "formula": "r_s = 2GM/c²",
    "description": "The radius of the event horizon of a non-rotating black hole.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 81,
    "name": "Gravitational Redshift",
    "formula": "z = Δλ/λ = GM/(rc²)",
    "description": "The shift in wavelength of light due to gravitational field.",
    "category": "Principle",
    "subject": "Physics"
  },
  {
    "id": 82,
    "name": "Escape Velocity",
    "formula": "v_esc = √(2GM/r)",
    "description": "The minimum velocity needed to escape gravitational field of a massive body.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 83,
    "name": "Orbital Velocity",
    "formula": "v = √(GM/r)",
    "description": "The velocity required for a satellite to maintain circular orbit.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 84,
    "name": "Kepler's First Law",
    "formula": "Planets orbit in ellipses with Sun at one focus",
    "description": "The path of each planet around the Sun is an ellipse with the Sun at one focus.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 85,
    "name": "Kepler's Second Law",
    "formula": "dA/dt = constant",
    "description": "A line joining a planet and the Sun sweeps equal areas in equal times.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 86,
    "name": "Kepler's Third Law",
    "formula": "T² ∝ r³",
    "description": "The square of orbital period is proportional to cube of semi-major axis.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 87,
    "name": "Reynolds Number",
    "formula": "Re = ρvL/μ",
    "description": "Dimensionless number predicting flow regime (laminar vs turbulent) in fluid dynamics.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 88,
    "name": "Poiseuille's Law",
    "formula": "Q = (πr⁴ΔP)/(8ηL)",
    "description": "The volumetric flow rate through a pipe depends on pressure difference and pipe geometry.",
    "category": "Law",
    "subject": "Physics"
  },
  {
    "id": 89,
    "name": "Surface Tension",
    "formula": "γ = F/L",
    "description": "The force per unit length acting along the boundary of a liquid surface.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 90,
    "name": "Young's Modulus",
    "formula": "E = σ/ε = (F/A)/(ΔL/L)",
    "description": "The ratio of stress to strain, measuring material stiffness.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 91,
    "name": "Shear Modulus",
    "formula": "G = τ/γ",
    "description": "The ratio of shear stress to shear strain, measuring resistance to shear deformation.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 92,
    "name": "Bulk Modulus",
    "formula": "K = -V(dP/dV)",
    "description": "The resistance of a material to uniform compression.",
    "category": "Formula",
    "subject": "Physics"
  },
  {
    "id": 93,
    "name": "Pythagorean Theorem",
    "formula": "a² + b² = c²",
    "description": "In a right triangle, the square of the hypotenuse equals the sum of squares of the other two sides.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 94,
    "name": "Fundamental Theorem of Calculus",
    "formula": "∫[a to b] f'(x)dx = f(b) - f(a)",
    "description": "The definite integral of a function's derivative over an interval equals the difference in the function's values at the endpoints.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 95,
    "name": "Mean Value Theorem",
    "formula": "f'(c) = (f(b) - f(a))/(b - a)",
    "description": "For a differentiable function on an interval, there exists a point where the instantaneous rate of change equals the average rate of change.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 96,
    "name": "Intermediate Value Theorem",
    "formula": "If f(a) < k < f(b), then ∃c: f(c) = k",
    "description": "A continuous function takes on every value between its values at two points.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 97,
    "name": "Binomial Theorem",
    "formula": "(a + b)ⁿ = Σ[k=0 to n] C(n,k) a^(n-k) b^k",
    "description": "Expands the power of a binomial expression into a sum of terms.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 98,
    "name": "Euler's Formula",
    "formula": "e^(iθ) = cos(θ) + i sin(θ)",
    "description": "Relates complex exponentials to trigonometric functions.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 99,
    "name": "Euler's Identity",
    "formula": "e^(iπ) + 1 = 0",
    "description": "A special case of Euler's formula, considered one of the most beautiful equations in mathematics.",
    "category": "Identity",
    "subject": "Mathematics"
  },
  {
    "id": 100,
    "name": "Quadratic Formula",
    "formula": "x = (-b ± √(b² - 4ac))/(2a)",
    "description": "Solves quadratic equations of the form ax² + bx + c = 0.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 101,
    "name": "Distance Formula",
    "formula": "d = √((x₂ - x₁)² + (y₂ - y₁)²)",
    "description": "Calculates the distance between two points in a coordinate plane.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 102,
    "name": "Slope Formula",
    "formula": "m = (y₂ - y₁)/(x₂ - x₁)",
    "description": "Calculates the slope of a line passing through two points.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 103,
    "name": "Area of Circle",
    "formula": "A = πr²",
    "description": "Calculates the area of a circle given its radius.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 104,
    "name": "Circumference of Circle",
    "formula": "C = 2πr",
    "description": "Calculates the perimeter of a circle given its radius.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 105,
    "name": "Volume of Sphere",
    "formula": "V = (4/3)πr³",
    "description": "Calculates the volume of a sphere given its radius.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 106,
    "name": "Surface Area of Sphere",
    "formula": "SA = 4πr²",
    "description": "Calculates the surface area of a sphere given its radius.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 107,
    "name": "Law of Sines",
    "formula": "a/sin(A) = b/sin(B) = c/sin(C)",
    "description": "Relates the sides and angles of any triangle.",
    "category": "Law",
    "subject": "Mathematics"
  },
  {
    "id": 108,
    "name": "Law of Cosines",
    "formula": "c² = a² + b² - 2ab cos(C)",
    "description": "Generalizes the Pythagorean theorem to any triangle.",
    "category": "Law",
    "subject": "Mathematics"
  },
  {
    "id": 109,
    "name": "Derivative of xⁿ",
    "formula": "d/dx(xⁿ) = nx^(n-1)",
    "description": "The power rule for differentiation.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 110,
    "name": "Product Rule",
    "formula": "d/dx(fg) = f'g + fg'",
    "description": "Rule for finding the derivative of a product of two functions.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 111,
    "name": "Quotient Rule",
    "formula": "d/dx(f/g) = (f'g - fg')/g²",
    "description": "Rule for finding the derivative of a quotient of two functions.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 112,
    "name": "Chain Rule",
    "formula": "d/dx(f(g(x))) = f'(g(x))·g'(x)",
    "description": "Rule for finding the derivative of a composite function.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 113,
    "name": "Integration by Parts",
    "formula": "∫u dv = uv - ∫v du",
    "description": "Technique for integrating the product of two functions.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 114,
    "name": "L'Hôpital's Rule",
    "formula": "lim[x→a] f(x)/g(x) = lim[x→a] f'(x)/g'(x)",
    "description": "Method for evaluating limits of indeterminate forms.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 115,
    "name": "Taylor Series",
    "formula": "f(x) = Σ[n=0 to ∞] (f^(n)(a)/n!)(x - a)ⁿ",
    "description": "Represents a function as an infinite sum of terms calculated from its derivatives at a point.",
    "category": "Series",
    "subject": "Mathematics"
  },
  {
    "id": 116,
    "name": "Fourier Series",
    "formula": "f(x) = a₀/2 + Σ[n=1 to ∞] (aₙcos(nx) + bₙsin(nx))",
    "description": "Represents a periodic function as a sum of sine and cosine functions.",
    "category": "Series",
    "subject": "Mathematics"
  },
  {
    "id": 117,
    "name": "Bayes' Theorem",
    "formula": "P(A|B) = P(B|A)·P(A)/P(B)",
    "description": "Describes the probability of an event based on prior knowledge of conditions related to the event.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 118,
    "name": "Central Limit Theorem",
    "formula": "As n → ∞, sample mean → N(μ, σ²/n)",
    "description": "The distribution of sample means approaches a normal distribution as sample size increases.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 119,
    "name": "Fermat's Last Theorem",
    "formula": "xⁿ + yⁿ = zⁿ has no integer solutions for n > 2",
    "description": "No three positive integers satisfy the equation for any integer power greater than 2.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 120,
    "name": "Gödel's Incompleteness Theorems",
    "formula": "Any consistent formal system is incomplete",
    "description": "In any sufficiently powerful formal system, there are true statements that cannot be proven within the system.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 121,
    "name": "Pythagorean Identity",
    "formula": "sin²(θ) + cos²(θ) = 1",
    "description": "Fundamental trigonometric identity relating sine and cosine.",
    "category": "Identity",
    "subject": "Mathematics"
  },
  {
    "id": 122,
    "name": "Sum of Angles Formula",
    "formula": "sin(A + B) = sin(A)cos(B) + cos(A)sin(B)",
    "description": "Formula for the sine of the sum of two angles.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 123,
    "name": "Logarithm Properties",
    "formula": "log(ab) = log(a) + log(b), log(a/b) = log(a) - log(b)",
    "description": "Fundamental properties of logarithms for multiplication and division.",
    "category": "Property",
    "subject": "Mathematics"
  },
  {
    "id": 124,
    "name": "Change of Base Formula",
    "formula": "log_b(x) = log_a(x)/log_a(b)",
    "description": "Converts logarithms from one base to another.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 125,
    "name": "Sum of Arithmetic Series",
    "formula": "S_n = n/2(a₁ + aₙ) = n/2(2a₁ + (n-1)d)",
    "description": "Calculates the sum of the first n terms of an arithmetic sequence.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 126,
    "name": "Sum of Geometric Series",
    "formula": "S_n = a₁(1 - rⁿ)/(1 - r)",
    "description": "Calculates the sum of the first n terms of a geometric sequence.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 127,
    "name": "Infinite Geometric Series",
    "formula": "S = a₁/(1 - r) for |r| < 1",
    "description": "Calculates the sum of an infinite geometric series when the common ratio is between -1 and 1.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 128,
    "name": "Euler's Number",
    "formula": "e = lim[n→∞] (1 + 1/n)ⁿ ≈ 2.71828",
    "description": "The base of natural logarithms, fundamental in calculus and exponential growth.",
    "category": "Constant",
    "subject": "Mathematics"
  },
  {
    "id": 129,
    "name": "Golden Ratio",
    "formula": "φ = (1 + √5)/2 ≈ 1.618",
    "description": "The ratio where the whole is to the larger part as the larger part is to the smaller part.",
    "category": "Constant",
    "subject": "Mathematics"
  },
  {
    "id": 130,
    "name": "Fibonacci Sequence",
    "formula": "Fₙ = Fₙ₋₁ + Fₙ₋₂",
    "description": "A sequence where each number is the sum of the two preceding ones, starting from 0 and 1.",
    "category": "Sequence",
    "subject": "Mathematics"
  },
  {
    "id": 131,
    "name": "Area of Triangle",
    "formula": "A = (1/2)bh = (1/2)ab sin(C)",
    "description": "The area of a triangle equals half the product of base and height, or half the product of two sides and sine of included angle.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 132,
    "name": "Area of Rectangle",
    "formula": "A = lw",
    "description": "The area of a rectangle equals length times width.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 133,
    "name": "Area of Parallelogram",
    "formula": "A = bh",
    "description": "The area of a parallelogram equals base times height.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 134,
    "name": "Area of Trapezoid",
    "formula": "A = (1/2)(a + b)h",
    "description": "The area of a trapezoid equals half the sum of parallel sides times height.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 135,
    "name": "Volume of Cylinder",
    "formula": "V = πr²h",
    "description": "The volume of a cylinder equals the area of circular base times height.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 136,
    "name": "Volume of Cone",
    "formula": "V = (1/3)πr²h",
    "description": "The volume of a cone equals one-third the volume of a cylinder with same base and height.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 137,
    "name": "Surface Area of Cylinder",
    "formula": "SA = 2πr² + 2πrh",
    "description": "The total surface area of a cylinder equals two circular bases plus lateral surface.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 138,
    "name": "Surface Area of Cone",
    "formula": "SA = πr² + πr√(r² + h²)",
    "description": "The total surface area of a cone equals base area plus lateral surface area.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 139,
    "name": "Volume of Pyramid",
    "formula": "V = (1/3)Bh",
    "description": "The volume of a pyramid equals one-third the product of base area and height.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 140,
    "name": "Midpoint Formula",
    "formula": "M = ((x₁ + x₂)/2, (y₁ + y₂)/2)",
    "description": "Finds the midpoint between two points in a coordinate plane.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 141,
    "name": "Equation of Circle",
    "formula": "(x - h)² + (y - k)² = r²",
    "description": "The standard form equation of a circle with center (h,k) and radius r.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 142,
    "name": "Equation of Ellipse",
    "formula": "(x-h)²/a² + (y-k)²/b² = 1",
    "description": "The standard form equation of an ellipse centered at (h,k) with semi-axes a and b.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 143,
    "name": "Equation of Parabola",
    "formula": "y = a(x-h)² + k",
    "description": "The vertex form equation of a parabola with vertex (h,k) and vertical axis.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 144,
    "name": "Equation of Hyperbola",
    "formula": "(x-h)²/a² - (y-k)²/b² = 1",
    "description": "The standard form equation of a hyperbola centered at (h,k).",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 145,
    "name": "Derivative of e^x",
    "formula": "d/dx(e^x) = e^x",
    "description": "The exponential function is its own derivative.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 146,
    "name": "Derivative of ln(x)",
    "formula": "d/dx(ln(x)) = 1/x",
    "description": "The derivative of natural logarithm is the reciprocal function.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 147,
    "name": "Derivative of sin(x)",
    "formula": "d/dx(sin(x)) = cos(x)",
    "description": "The derivative of sine is cosine.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 148,
    "name": "Derivative of cos(x)",
    "formula": "d/dx(cos(x)) = -sin(x)",
    "description": "The derivative of cosine is negative sine.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 149,
    "name": "Derivative of tan(x)",
    "formula": "d/dx(tan(x)) = sec²(x)",
    "description": "The derivative of tangent is secant squared.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 150,
    "name": "Integration of 1/x",
    "formula": "∫(1/x)dx = ln|x| + C",
    "description": "The integral of reciprocal function is natural logarithm of absolute value.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 151,
    "name": "Integration by Substitution",
    "formula": "∫f(g(x))g'(x)dx = ∫f(u)du",
    "description": "Technique for integration using substitution u = g(x).",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 152,
    "name": "Fundamental Theorem of Algebra",
    "formula": "Every polynomial of degree n has exactly n complex roots",
    "description": "A polynomial equation of degree n has exactly n roots in the complex number system.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 153,
    "name": "Remainder Theorem",
    "formula": "P(a) = remainder when P(x) is divided by (x-a)",
    "description": "When a polynomial P(x) is divided by (x-a), the remainder is P(a).",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 154,
    "name": "Factor Theorem",
    "formula": "If P(a) = 0, then (x-a) is a factor of P(x)",
    "description": "A polynomial has (x-a) as a factor if and only if P(a) = 0.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 155,
    "name": "Rational Root Theorem",
    "formula": "Possible rational roots = ±(factors of constant)/(factors of leading coefficient)",
    "description": "Lists all possible rational roots of a polynomial equation with integer coefficients.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 156,
    "name": "Pascal's Triangle",
    "formula": "Each number is sum of two numbers directly above it",
    "description": "A triangular array of binomial coefficients used in combinatorics and algebra.",
    "category": "Principle",
    "subject": "Mathematics"
  },
  {
    "id": 157,
    "name": "Permutation Formula",
    "formula": "P(n,r) = n!/(n-r)!",
    "description": "The number of ways to arrange r objects from n distinct objects.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 158,
    "name": "Combination Formula",
    "formula": "C(n,r) = n!/(r!(n-r)!)",
    "description": "The number of ways to choose r objects from n distinct objects without regard to order.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 159,
    "name": "Binomial Coefficient",
    "formula": "C(n,k) = n!/(k!(n-k)!)",
    "description": "The coefficient of x^k in expansion of (1+x)^n, also written as (n choose k).",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 160,
    "name": "Expected Value",
    "formula": "E[X] = Σx·P(x)",
    "description": "The average value of a random variable, weighted by probability distribution.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 161,
    "name": "Variance",
    "formula": "Var(X) = E[X²] - (E[X])²",
    "description": "The measure of spread or dispersion of a probability distribution.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 162,
    "name": "Standard Deviation",
    "formula": "σ = √Var(X)",
    "description": "The square root of variance, measuring spread in same units as the variable.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 163,
    "name": "Normal Distribution",
    "formula": "f(x) = (1/(σ√(2π)))e^(-(x-μ)²/(2σ²))",
    "description": "The probability density function of the bell-shaped normal distribution.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 164,
    "name": "Z-Score",
    "formula": "z = (x - μ)/σ",
    "description": "The number of standard deviations a value is from the mean in a normal distribution.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 165,
    "name": "Correlation Coefficient",
    "formula": "r = Σ((x-x̄)(y-ȳ))/(√(Σ(x-x̄)²)√(Σ(y-ȳ)²))",
    "description": "Measures the strength and direction of linear relationship between two variables.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 166,
    "name": "Linear Regression Slope",
    "formula": "m = r(σ_y/σ_x)",
    "description": "The slope of the least-squares regression line relating two variables.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 167,
    "name": "Matrix Multiplication",
    "formula": "(AB)_ij = ΣA_ik B_kj",
    "description": "The element in row i, column j of product matrix equals sum of products of corresponding elements.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 168,
    "name": "Determinant of 2x2 Matrix",
    "formula": "det(A) = ad - bc",
    "description": "For matrix [[a,b],[c,d]], the determinant equals ad minus bc.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 169,
    "name": "Inverse of 2x2 Matrix",
    "formula": "A⁻¹ = (1/det(A))[[d,-b],[-c,a]]",
    "description": "The inverse of a 2x2 matrix, if determinant is non-zero.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 170,
    "name": "Dot Product",
    "formula": "a·b = |a||b|cos(θ) = Σa_i b_i",
    "description": "The scalar product of two vectors, equal to product of magnitudes and cosine of angle.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 171,
    "name": "Cross Product",
    "formula": "a × b = |a||b|sin(θ)n",
    "description": "The vector product of two vectors, perpendicular to both, with magnitude equal to area of parallelogram.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 172,
    "name": "Magnitude of Vector",
    "formula": "|v| = √(v₁² + v₂² + v₃²)",
    "description": "The length or magnitude of a vector in three-dimensional space.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 173,
    "name": "Unit Vector",
    "formula": "û = v/|v|",
    "description": "A vector with magnitude 1, pointing in same direction as original vector.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 174,
    "name": "Polar to Cartesian Conversion",
    "formula": "x = r cos(θ), y = r sin(θ)",
    "description": "Converts polar coordinates (r,θ) to Cartesian coordinates (x,y).",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 175,
    "name": "Cartesian to Polar Conversion",
    "formula": "r = √(x² + y²), θ = arctan(y/x)",
    "description": "Converts Cartesian coordinates (x,y) to polar coordinates (r,θ).",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 176,
    "name": "Euler's Totient Function",
    "formula": "φ(n) = n × Π(1 - 1/p) for prime factors p",
    "description": "Counts positive integers up to n that are relatively prime to n.",
    "category": "Function",
    "subject": "Mathematics"
  },
  {
    "id": 177,
    "name": "Fermat's Little Theorem",
    "formula": "a^(p-1) ≡ 1 (mod p) for prime p and gcd(a,p)=1",
    "description": "If p is prime and a is not divisible by p, then a raised to (p-1) is congruent to 1 modulo p.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 178,
    "name": "Chinese Remainder Theorem",
    "formula": "System x ≡ a_i (mod n_i) has unique solution modulo product of n_i",
    "description": "Provides conditions for existence and uniqueness of solutions to simultaneous congruences.",
    "category": "Theorem",
    "subject": "Mathematics"
  },
  {
    "id": 179,
    "name": "L'Hôpital's Rule (Extended)",
    "formula": "lim f/g = lim f'/g' = lim f''/g'' = ...",
    "description": "Can be applied repeatedly if first application yields indeterminate form.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 180,
    "name": "Maclaurin Series",
    "formula": "f(x) = Σ[n=0 to ∞] (f^(n)(0)/n!)x^n",
    "description": "Taylor series expansion centered at zero, representing function as infinite polynomial.",
    "category": "Series",
    "subject": "Mathematics"
  },
  {
    "id": 181,
    "name": "Geometric Series Sum",
    "formula": "Σ[n=0 to ∞] ar^n = a/(1-r) for |r| < 1",
    "description": "The sum of infinite geometric series converges when common ratio has absolute value less than 1.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 182,
    "name": "Riemann Sum",
    "formula": "Σ f(x_i*)Δx",
    "description": "Approximation of definite integral using sum of function values times subinterval widths.",
    "category": "Formula",
    "subject": "Mathematics"
  },
  {
    "id": 183,
    "name": "Trapezoidal Rule",
    "formula": "∫[a to b] f(x)dx ≈ (b-a)/2n [f(x₀) + 2Σf(x_i) + f(x_n)]",
    "description": "Numerical integration method approximating area under curve using trapezoids.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 184,
    "name": "Simpson's Rule",
    "formula": "∫[a to b] f(x)dx ≈ (b-a)/6n [f(x₀) + 4Σf(x_odd) + 2Σf(x_even) + f(x_n)]",
    "description": "Numerical integration method using parabolic approximations, more accurate than trapezoidal rule.",
    "category": "Rule",
    "subject": "Mathematics"
  },
  {
    "id": 185,
    "name": "Cell Theory",
    "formula": "All living things are composed of cells; cells are the basic unit of life; cells arise from pre-existing cells",
    "description": "The fundamental principle that all living organisms are composed of one or more cells, and that cells are the basic structural and functional units of life.",
    "category": "Theory",
    "subject": "Biology"
  },
  {
    "id": 186,
    "name": "Theory of Evolution by Natural Selection",
    "formula": "Variation + Inheritance + Selection = Evolution",
    "description": "Organisms with traits better suited to their environment are more likely to survive and reproduce, passing those traits to offspring.",
    "category": "Theory",
    "subject": "Biology"
  },
  {
    "id": 187,
    "name": "Mendel's Laws of Inheritance",
    "formula": "Law of Segregation: Alleles separate during gamete formation; Law of Independent Assortment: Genes for different traits assort independently",
    "description": "Fundamental principles of genetics describing how traits are inherited from parents to offspring.",
    "category": "Law",
    "subject": "Biology"
  },
  {
    "id": 188,
    "name": "Hardy-Weinberg Principle",
    "formula": "p² + 2pq + q² = 1",
    "description": "In a population with no evolutionary forces, allele and genotype frequencies remain constant from generation to generation.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 189,
    "name": "Central Dogma of Molecular Biology",
    "formula": "DNA → RNA → Protein",
    "description": "The flow of genetic information from DNA to RNA to protein, with DNA replication as the exception.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 190,
    "name": "Watson-Crick Base Pairing",
    "formula": "A-T (2 H-bonds), G-C (3 H-bonds)",
    "description": "The specific pairing of nucleotide bases in DNA: adenine with thymine, and guanine with cytosine.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 191,
    "name": "Chargaff's Rules",
    "formula": "A = T, G = C, (A + G) = (T + C)",
    "description": "In DNA, the amount of adenine equals thymine, and guanine equals cytosine.",
    "category": "Rule",
    "subject": "Biology"
  },
  {
    "id": 192,
    "name": "Michaelis-Menten Equation",
    "formula": "v = (V_max × [S])/(K_m + [S])",
    "description": "Describes the rate of enzymatic reactions as a function of substrate concentration.",
    "category": "Equation",
    "subject": "Biology"
  },
  {
    "id": 193,
    "name": "Photosynthesis Equation",
    "formula": "6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂",
    "description": "The process by which plants convert carbon dioxide and water into glucose using light energy.",
    "category": "Equation",
    "subject": "Biology"
  },
  {
    "id": 194,
    "name": "Cellular Respiration Equation",
    "formula": "C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + ATP",
    "description": "The process by which cells break down glucose to produce ATP (energy) in the presence of oxygen.",
    "category": "Equation",
    "subject": "Biology"
  },
  {
    "id": 195,
    "name": "ATP Production Formula",
    "formula": "ATP = ADP + Pᵢ + energy",
    "description": "Adenosine triphosphate is formed from adenosine diphosphate and inorganic phosphate, storing energy.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 196,
    "name": "Population Growth (Exponential)",
    "formula": "N(t) = N₀e^(rt)",
    "description": "Describes population growth when resources are unlimited, where r is the growth rate.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 197,
    "name": "Logistic Growth Model",
    "formula": "dN/dt = rN(1 - N/K)",
    "description": "Describes population growth with carrying capacity K, showing S-shaped growth curve.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 198,
    "name": "Nernst Equation",
    "formula": "E = E° - (RT/nF)ln(Q)",
    "description": "Calculates the equilibrium potential for an ion across a membrane based on concentration gradient.",
    "category": "Equation",
    "subject": "Biology"
  },
  {
    "id": 199,
    "name": "Fick's Law of Diffusion",
    "formula": "J = -D(dC/dx)",
    "description": "The rate of diffusion is proportional to the concentration gradient and inversely proportional to distance.",
    "category": "Law",
    "subject": "Biology"
  },
  {
    "id": 200,
    "name": "Boyle's Law (Biological Application)",
    "formula": "P₁V₁ = P₂V₂",
    "description": "In respiratory physiology, the relationship between pressure and volume in the lungs.",
    "category": "Law",
    "subject": "Biology"
  },
  {
    "id": 201,
    "name": "Cardiac Output",
    "formula": "CO = HR × SV",
    "description": "The volume of blood pumped by the heart per minute, equal to heart rate times stroke volume.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 202,
    "name": "Blood Pressure",
    "formula": "BP = CO × TPR",
    "description": "Blood pressure equals cardiac output multiplied by total peripheral resistance.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 203,
    "name": "Genotype Frequency",
    "formula": "f(AA) = p², f(Aa) = 2pq, f(aa) = q²",
    "description": "In Hardy-Weinberg equilibrium, genotype frequencies are determined by allele frequencies.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 204,
    "name": "Allele Frequency",
    "formula": "p + q = 1",
    "description": "The sum of allele frequencies for a gene locus equals 1 in a population.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 205,
    "name": "Heritability",
    "formula": "h² = V_G/V_P",
    "description": "The proportion of phenotypic variance attributable to genetic variance.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 206,
    "name": "DNA Replication Semi-Conservative Model",
    "formula": "Parent DNA → 2 Daughter DNA (each with one old and one new strand)",
    "description": "Each DNA molecule consists of one original strand and one newly synthesized strand.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 207,
    "name": "Genetic Code",
    "formula": "64 codons code for 20 amino acids + 3 stop codons",
    "description": "The universal code by which nucleotide triplets (codons) specify amino acids in proteins.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 208,
    "name": "Allometric Scaling",
    "formula": "Y = aM^b",
    "description": "The relationship between body size and biological variables, often following power laws.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 209,
    "name": "Metabolic Rate (Kleiber's Law)",
    "formula": "BMR ∝ M^(3/4)",
    "description": "Basal metabolic rate scales to the 3/4 power of body mass across species.",
    "category": "Law",
    "subject": "Biology"
  },
  {
    "id": 210,
    "name": "Species-Area Relationship",
    "formula": "S = cA^z",
    "description": "The number of species increases with area, following a power law relationship.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 211,
    "name": "Lotka-Volterra Predator-Prey Model",
    "formula": "dN/dt = rN - aNP, dP/dt = baNP - mP",
    "description": "Mathematical model describing the dynamics of predator and prey populations.",
    "category": "Model",
    "subject": "Biology"
  },
  {
    "id": 212,
    "name": "Competitive Exclusion Principle",
    "formula": "Two species cannot occupy the same ecological niche indefinitely",
    "description": "When two species compete for the same limited resource, one will eventually outcompete the other.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 213,
    "name": "Ecological Succession",
    "formula": "Pioneer species → Intermediate species → Climax community",
    "description": "The process by which the structure of a biological community evolves over time.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 214,
    "name": "Homeostasis",
    "formula": "Set point → Sensor → Control center → Effector → Response",
    "description": "The maintenance of a stable internal environment despite external changes.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 215,
    "name": "Negative Feedback Loop",
    "formula": "Stimulus → Response → Reduced stimulus",
    "description": "A regulatory mechanism where the output reduces the initial stimulus, maintaining homeostasis.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 216,
    "name": "Positive Feedback Loop",
    "formula": "Stimulus → Response → Enhanced stimulus",
    "description": "A regulatory mechanism where the output amplifies the initial stimulus, leading to rapid change.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 217,
    "name": "DNA Replication Rate",
    "formula": "Rate ≈ 1000 nucleotides/second",
    "description": "The approximate rate at which DNA polymerase synthesizes new DNA strands during replication.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 218,
    "name": "Transcription Rate",
    "formula": "Rate ≈ 50-100 nucleotides/second",
    "description": "The approximate rate at which RNA polymerase synthesizes mRNA during transcription.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 219,
    "name": "Translation Rate",
    "formula": "Rate ≈ 15-20 amino acids/second",
    "description": "The approximate rate at which ribosomes synthesize proteins during translation.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 220,
    "name": "DNA Base Pairing Rules",
    "formula": "A-T (2 H-bonds), G-C (3 H-bonds)",
    "description": "The specific hydrogen bonding patterns between complementary nucleotide bases in DNA double helix.",
    "category": "Rule",
    "subject": "Biology"
  },
  {
    "id": 221,
    "name": "RNA Base Pairing Rules",
    "formula": "A-U, G-C (in RNA)",
    "description": "Base pairing rules in RNA, where uracil replaces thymine in pairing with adenine.",
    "category": "Rule",
    "subject": "Biology"
  },
  {
    "id": 222,
    "name": "Genetic Code Degeneracy",
    "formula": "64 codons code for 20 amino acids",
    "description": "Multiple codons can code for the same amino acid, providing redundancy in genetic code.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 223,
    "name": "Mendel's Law of Segregation",
    "formula": "Alleles separate during gamete formation",
    "description": "During gamete formation, the two alleles for a trait separate, with each gamete receiving one allele.",
    "category": "Law",
    "subject": "Biology"
  },
  {
    "id": 224,
    "name": "Mendel's Law of Independent Assortment",
    "formula": "Genes for different traits assort independently",
    "description": "Genes for different traits are inherited independently of each other during gamete formation.",
    "category": "Law",
    "subject": "Biology"
  },
  {
    "id": 225,
    "name": "Punnett Square",
    "formula": "2×2 grid showing all possible genotype combinations",
    "description": "A diagram used to predict the genotypes and phenotypes of offspring from a genetic cross.",
    "category": "Method",
    "subject": "Biology"
  },
  {
    "id": 226,
    "name": "Chi-Square Test",
    "formula": "χ² = Σ((O - E)²/E)",
    "description": "Statistical test to determine if observed data matches expected Mendelian ratios.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 227,
    "name": "Linkage and Recombination",
    "formula": "Recombination frequency = (recombinants/total) × 100%",
    "description": "Genes on same chromosome are linked; recombination frequency indicates distance between genes.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 228,
    "name": "Hardy-Weinberg Equilibrium Conditions",
    "formula": "No mutation, migration, selection, genetic drift, or non-random mating",
    "description": "Five conditions required for allele frequencies to remain constant from generation to generation.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 229,
    "name": "Natural Selection",
    "formula": "differential survival and reproduction of individuals with favorable traits",
    "description": "The mechanism of evolution where organisms with advantageous traits are more likely to survive and reproduce.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 230,
    "name": "Fitness",
    "formula": "Relative reproductive success",
    "description": "The ability of an organism to survive and reproduce in its environment, relative to others.",
    "category": "Concept",
    "subject": "Biology"
  },
  {
    "id": 231,
    "name": "Selection Coefficient",
    "formula": "s = 1 - w",
    "description": "The reduction in fitness of a genotype relative to the fittest genotype, where w is relative fitness.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 232,
    "name": "Mutation Rate",
    "formula": "μ = mutations per generation per base pair",
    "description": "The frequency at which mutations occur in DNA sequences.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 233,
    "name": "Genetic Drift",
    "formula": "Random changes in allele frequencies due to sampling",
    "description": "The random fluctuation of allele frequencies in small populations due to chance events.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 234,
    "name": "Founder Effect",
    "formula": "Small founding population → reduced genetic diversity",
    "description": "When a small group establishes a new population, genetic diversity is reduced compared to source population.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 235,
    "name": "Bottleneck Effect",
    "formula": "Population crash → reduced genetic diversity",
    "description": "When a population undergoes severe reduction, genetic diversity decreases dramatically.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 236,
    "name": "Gene Flow",
    "formula": "Migration introduces new alleles",
    "description": "The transfer of genetic variation from one population to another through migration.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 237,
    "name": "Speciation",
    "formula": "Reproductive isolation → new species",
    "description": "The process by which populations evolve to become distinct species, typically through reproductive isolation.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 238,
    "name": "Allopatric Speciation",
    "formula": "Geographic isolation → speciation",
    "description": "Speciation that occurs when populations are geographically separated.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 239,
    "name": "Sympatric Speciation",
    "formula": "Speciation without geographic isolation",
    "description": "Speciation that occurs in the same geographic area, often through polyploidy or habitat specialization.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 240,
    "name": "Ecological Niche",
    "formula": "The role and position of a species in its environment",
    "description": "The ecological role of a species, including its habitat, resources used, and interactions with other species.",
    "category": "Concept",
    "subject": "Biology"
  },
  {
    "id": 241,
    "name": "Trophic Level Efficiency",
    "formula": "Efficiency ≈ 10%",
    "description": "Only about 10% of energy is transferred from one trophic level to the next in food chains.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 242,
    "name": "Carrying Capacity",
    "formula": "K = maximum population size environment can support",
    "description": "The maximum number of individuals of a species that an environment can sustain indefinitely.",
    "category": "Concept",
    "subject": "Biology"
  },
  {
    "id": 243,
    "name": "Exponential Growth",
    "formula": "dN/dt = rN",
    "description": "Population growth when resources are unlimited, resulting in exponential increase.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 244,
    "name": "Logistic Growth",
    "formula": "dN/dt = rN(1 - N/K)",
    "description": "Population growth with carrying capacity, showing S-shaped curve.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 245,
    "name": "Intrinsic Growth Rate",
    "formula": "r = birth rate - death rate",
    "description": "The maximum per capita growth rate of a population under ideal conditions.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 246,
    "name": "Biomass Pyramid",
    "formula": "Producers > Primary consumers > Secondary consumers",
    "description": "The decrease in total biomass at each successive trophic level in an ecosystem.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 247,
    "name": "Primary Productivity",
    "formula": "GPP = NPP + R",
    "description": "Gross primary productivity equals net primary productivity plus respiration.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 248,
    "name": "Net Primary Productivity",
    "formula": "NPP = GPP - R",
    "description": "The rate at which energy is stored by producers after accounting for respiration.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 249,
    "name": "Carbon Cycle",
    "formula": "CO₂ ↔ Organic compounds ↔ CO₂",
    "description": "The biogeochemical cycle by which carbon moves between atmosphere, organisms, and Earth.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 250,
    "name": "Nitrogen Cycle",
    "formula": "N₂ → NH₃ → NO₂⁻ → NO₃⁻ → Organic N",
    "description": "The biogeochemical cycle converting atmospheric nitrogen into forms usable by organisms.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 251,
    "name": "Phosphorus Cycle",
    "formula": "Rocks → Soil → Plants → Animals → Decomposers",
    "description": "The biogeochemical cycle moving phosphorus through lithosphere, hydrosphere, and biosphere.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 252,
    "name": "Water Cycle",
    "formula": "Evaporation → Condensation → Precipitation → Runoff",
    "description": "The continuous movement of water through Earth's systems via evaporation, condensation, and precipitation.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 253,
    "name": "Osmotic Pressure",
    "formula": "π = iMRT",
    "description": "The pressure required to prevent osmosis, where i is van't Hoff factor, M is molarity.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 254,
    "name": "Osmosis",
    "formula": "Water moves from low to high solute concentration",
    "description": "The passive movement of water across a semipermeable membrane from low to high solute concentration.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 255,
    "name": "Diffusion",
    "formula": "J = -D(dC/dx)",
    "description": "The passive movement of particles from high to low concentration, following Fick's law.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 256,
    "name": "Active Transport",
    "formula": "Requires ATP to move against concentration gradient",
    "description": "The movement of molecules across membrane against concentration gradient, requiring energy input.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 257,
    "name": "Facilitated Diffusion",
    "formula": "Passive transport via carrier proteins",
    "description": "The passive movement of molecules across membrane through protein channels or carriers.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 258,
    "name": "Enzyme Kinetics - Vmax",
    "formula": "V_max = k_cat[E]_total",
    "description": "The maximum reaction rate when enzyme is saturated with substrate.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 259,
    "name": "Enzyme Kinetics - Km",
    "formula": "K_m = (k_{-1} + k_2)/k_1",
    "description": "The Michaelis constant, equal to substrate concentration at half-maximal velocity.",
    "category": "Constant",
    "subject": "Biology"
  },
  {
    "id": 260,
    "name": "Enzyme Efficiency",
    "formula": "k_cat/K_m",
    "description": "The catalytic efficiency of an enzyme, measuring how well it converts substrate to product.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 261,
    "name": "Lineweaver-Burk Plot",
    "formula": "1/v = (K_m/V_max)(1/[S]) + 1/V_max",
    "description": "Double reciprocal plot used to determine V_max and K_m from enzyme kinetics data.",
    "category": "Method",
    "subject": "Biology"
  },
  {
    "id": 262,
    "name": "Allosteric Regulation",
    "formula": "Binding at one site affects activity at another site",
    "description": "Regulation of enzyme activity through binding of effector molecules at sites other than active site.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 263,
    "name": "Cooperativity",
    "formula": "Binding of one ligand increases affinity for others",
    "description": "The phenomenon where binding of one substrate molecule increases enzyme's affinity for additional substrates.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 264,
    "name": "Hill Coefficient",
    "formula": "n_H = measure of cooperativity",
    "description": "A measure of cooperativity in enzyme kinetics; n_H > 1 indicates positive cooperativity.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 265,
    "name": "Gibbs Free Energy in Biochemistry",
    "formula": "ΔG = ΔG°' + RT ln([products]/[reactants])",
    "description": "The change in free energy for biochemical reactions, accounting for standard conditions and concentrations.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 266,
    "name": "ATP Hydrolysis",
    "formula": "ATP + H₂O → ADP + Pᵢ, ΔG ≈ -30.5 kJ/mol",
    "description": "The hydrolysis of ATP releases energy used to drive endergonic reactions in cells.",
    "category": "Equation",
    "subject": "Biology"
  },
  {
    "id": 267,
    "name": "Redox Potential",
    "formula": "E = E°' - (RT/nF)ln([reduced]/[oxidized])",
    "description": "The tendency of a chemical species to gain electrons, determining direction of redox reactions.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 268,
    "name": "Glycolysis Net ATP",
    "formula": "2 ATP per glucose molecule",
    "description": "The net ATP production from glycolysis, producing 4 ATP but consuming 2 ATP.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 269,
    "name": "Citric Acid Cycle ATP Yield",
    "formula": "1 ATP, 3 NADH, 1 FADH₂ per acetyl-CoA",
    "description": "The energy carriers produced per turn of citric acid cycle from one acetyl-CoA molecule.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 270,
    "name": "Oxidative Phosphorylation ATP",
    "formula": "~2.5 ATP per NADH, ~1.5 ATP per FADH₂",
    "description": "The approximate ATP yield from electron transport chain per reduced coenzyme.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 271,
    "name": "Total ATP from Glucose",
    "formula": "~30-32 ATP per glucose molecule",
    "description": "The total ATP yield from complete oxidation of one glucose molecule through cellular respiration.",
    "category": "Formula",
    "subject": "Biology"
  },
  {
    "id": 272,
    "name": "Calvin Cycle",
    "formula": "3 CO₂ + 9 ATP + 6 NADPH → G3P + 9 ADP + 6 NADP⁺",
    "description": "The light-independent reactions of photosynthesis that fix carbon dioxide into organic molecules.",
    "category": "Equation",
    "subject": "Biology"
  },
  {
    "id": 273,
    "name": "Light Reactions",
    "formula": "H₂O + NADP⁺ + ADP + Pᵢ → O₂ + NADPH + ATP",
    "description": "The light-dependent reactions of photosynthesis that produce ATP and NADPH.",
    "category": "Equation",
    "subject": "Biology"
  },
  {
    "id": 274,
    "name": "Chlorophyll Absorption",
    "formula": "Absorbs red (680nm) and blue (430nm) light",
    "description": "Chlorophyll molecules absorb light most efficiently in red and blue wavelengths, reflecting green.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 275,
    "name": "Action Spectrum",
    "formula": "Rate of photosynthesis vs wavelength",
    "description": "The effectiveness of different wavelengths of light in driving photosynthesis.",
    "category": "Concept",
    "subject": "Biology"
  },
  {
    "id": 276,
    "name": "Photorespiration",
    "formula": "Rubisco fixes O₂ instead of CO₂",
    "description": "A wasteful process where rubisco binds oxygen instead of carbon dioxide, reducing photosynthetic efficiency.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 277,
    "name": "C4 Photosynthesis",
    "formula": "CO₂ fixed into 4-carbon compound first",
    "description": "A photosynthetic pathway that minimizes photorespiration by initially fixing CO₂ into 4-carbon compounds.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 278,
    "name": "CAM Photosynthesis",
    "formula": "CO₂ fixed at night, used during day",
    "description": "Crassulacean acid metabolism where plants fix CO₂ at night and use it during the day to minimize water loss.",
    "category": "Principle",
    "subject": "Biology"
  },
  {
    "id": 279,
    "name": "Avogadro's Law",
    "formula": "V ∝ n (at constant T and P)",
    "description": "Equal volumes of gases at the same temperature and pressure contain equal numbers of molecules.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 280,
    "name": "Avogadro's Number",
    "formula": "N_A = 6.022 × 10²³ mol⁻¹",
    "description": "The number of particles (atoms, molecules, ions) in one mole of a substance.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 281,
    "name": "Ideal Gas Law",
    "formula": "PV = nRT",
    "description": "The relationship between pressure, volume, temperature, and number of moles of an ideal gas.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 282,
    "name": "Combined Gas Law",
    "formula": "P₁V₁/T₁ = P₂V₂/T₂",
    "description": "Combines Boyle's, Charles's, and Gay-Lussac's laws into a single equation.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 283,
    "name": "Dalton's Law of Partial Pressures",
    "formula": "P_total = P₁ + P₂ + P₃ + ...",
    "description": "The total pressure of a mixture of gases equals the sum of the partial pressures of the individual gases.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 284,
    "name": "Graham's Law of Effusion",
    "formula": "Rate₁/Rate₂ = √(M₂/M₁)",
    "description": "The rate of effusion of a gas is inversely proportional to the square root of its molar mass.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 285,
    "name": "Raoult's Law",
    "formula": "P = X_solvent × P°_solvent",
    "description": "The vapor pressure of a solution is proportional to the mole fraction of the solvent.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 286,
    "name": "Henry's Law",
    "formula": "C = k_H × P",
    "description": "The amount of gas dissolved in a liquid is proportional to the partial pressure of the gas above the liquid.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 287,
    "name": "Hess's Law",
    "formula": "ΔH_reaction = ΣΔH_products - ΣΔH_reactants",
    "description": "The total enthalpy change for a reaction is independent of the pathway taken.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 288,
    "name": "First Law of Thermodynamics (Chemistry)",
    "formula": "ΔU = q + w",
    "description": "The change in internal energy equals the heat added to the system plus the work done on the system.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 289,
    "name": "Gibbs Free Energy",
    "formula": "ΔG = ΔH - TΔS",
    "description": "The energy available to do work in a chemical reaction, determining spontaneity.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 290,
    "name": "Entropy Change",
    "formula": "ΔS = q_rev/T",
    "description": "The measure of disorder or randomness in a system, related to reversible heat transfer.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 291,
    "name": "Arrhenius Equation",
    "formula": "k = Ae^(-E_a/RT)",
    "description": "Describes the temperature dependence of reaction rates, where E_a is activation energy.",
    "category": "Equation",
    "subject": "Chemistry"
  },
  {
    "id": 292,
    "name": "Rate Law",
    "formula": "Rate = k[A]^m[B]^n",
    "description": "The rate of a chemical reaction is proportional to the concentrations of reactants raised to their reaction orders.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 293,
    "name": "Equilibrium Constant (Kc)",
    "formula": "Kc = [C]^c[D]^d / [A]^a[B]^b",
    "description": "The ratio of product concentrations to reactant concentrations at equilibrium, each raised to their stoichiometric coefficients.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 294,
    "name": "Equilibrium Constant (Kp)",
    "formula": "Kp = (P_C^c)(P_D^d) / (P_A^a)(P_B^b)",
    "description": "The equilibrium constant expressed in terms of partial pressures for gas-phase reactions.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 295,
    "name": "Le Chatelier's Principle",
    "formula": "System responds to minimize stress",
    "description": "When a system at equilibrium is disturbed, it shifts to counteract the disturbance and restore equilibrium.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 296,
    "name": "pH Formula",
    "formula": "pH = -log[H⁺]",
    "description": "The negative logarithm of the hydrogen ion concentration, measuring acidity.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 297,
    "name": "pOH Formula",
    "formula": "pOH = -log[OH⁻]",
    "description": "The negative logarithm of the hydroxide ion concentration.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 298,
    "name": "pH + pOH Relationship",
    "formula": "pH + pOH = 14 (at 25°C)",
    "description": "The sum of pH and pOH equals 14 for aqueous solutions at standard temperature.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 299,
    "name": "Ion Product of Water",
    "formula": "K_w = [H⁺][OH⁻] = 1.0 × 10⁻¹⁴",
    "description": "The product of hydrogen and hydroxide ion concentrations in water at 25°C.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 300,
    "name": "Acid Dissociation Constant (Ka)",
    "formula": "Ka = [H⁺][A⁻] / [HA]",
    "description": "The equilibrium constant for the dissociation of a weak acid.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 301,
    "name": "Base Dissociation Constant (Kb)",
    "formula": "Kb = [OH⁻][BH⁺] / [B]",
    "description": "The equilibrium constant for the dissociation of a weak base.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 302,
    "name": "Henderson-Hasselbalch Equation",
    "formula": "pH = pKa + log([A⁻]/[HA])",
    "description": "Relates the pH of a buffer solution to the pKa and the ratio of conjugate base to acid.",
    "category": "Equation",
    "subject": "Chemistry"
  },
  {
    "id": 303,
    "name": "Nernst Equation (Electrochemistry)",
    "formula": "E = E° - (RT/nF)ln(Q)",
    "description": "Calculates the cell potential under non-standard conditions based on the reaction quotient.",
    "category": "Equation",
    "subject": "Chemistry"
  },
  {
    "id": 304,
    "name": "Faraday's Law of Electrolysis",
    "formula": "m = (M × I × t) / (n × F)",
    "description": "The mass of substance deposited or liberated at an electrode is proportional to the charge passed.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 305,
    "name": "Standard Cell Potential",
    "formula": "E°_cell = E°_cathode - E°_anode",
    "description": "The difference between standard reduction potentials of cathode and anode half-cells.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 306,
    "name": "Free Energy and Cell Potential",
    "formula": "ΔG = -nFE",
    "description": "The relationship between Gibbs free energy change and cell potential.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 307,
    "name": "Molarity",
    "formula": "M = n/V",
    "description": "The number of moles of solute per liter of solution.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 308,
    "name": "Molality",
    "formula": "m = n_solute / m_solvent (kg)",
    "description": "The number of moles of solute per kilogram of solvent.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 309,
    "name": "Mole Fraction",
    "formula": "X_A = n_A / (n_A + n_B + ...)",
    "description": "The ratio of the number of moles of a component to the total number of moles in the mixture.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 310,
    "name": "Percent Composition",
    "formula": "% = (mass of element / mass of compound) × 100",
    "description": "The percentage by mass of each element in a compound.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 311,
    "name": "Empirical Formula",
    "formula": "Simplest whole number ratio of atoms",
    "description": "The simplest ratio of elements in a compound, determined from percent composition.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 312,
    "name": "Molecular Formula",
    "formula": "Molecular formula = (Empirical formula) × n",
    "description": "The actual number of atoms of each element in a molecule, a multiple of the empirical formula.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 313,
    "name": "Stoichiometry",
    "formula": "Based on balanced chemical equation coefficients",
    "description": "The quantitative relationship between reactants and products in a chemical reaction.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 314,
    "name": "Limiting Reactant",
    "formula": "The reactant that is completely consumed first",
    "description": "The reactant that determines the maximum amount of product that can be formed in a reaction.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 315,
    "name": "Theoretical Yield",
    "formula": "Based on limiting reactant and stoichiometry",
    "description": "The maximum amount of product that can be obtained from a reaction under ideal conditions.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 316,
    "name": "Percent Yield",
    "formula": "% Yield = (Actual yield / Theoretical yield) × 100",
    "description": "The ratio of actual yield to theoretical yield, expressed as a percentage.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 317,
    "name": "Beer-Lambert Law",
    "formula": "A = εlc",
    "description": "The absorbance of light is proportional to the concentration and path length of the absorbing species.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 318,
    "name": "Planck's Constant",
    "formula": "h = 6.626 × 10⁻³⁴ J·s",
    "description": "The fundamental constant relating the energy of a photon to its frequency.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 319,
    "name": "Rydberg Formula",
    "formula": "1/λ = R(1/n₁² - 1/n₂²)",
    "description": "Calculates the wavelength of light emitted or absorbed when an electron transitions between energy levels.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 320,
    "name": "de Broglie Wavelength (Chemistry)",
    "formula": "λ = h/(mv)",
    "description": "All matter exhibits wave-like properties, with wavelength inversely proportional to momentum.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 321,
    "name": "Heisenberg Uncertainty Principle (Chemistry)",
    "formula": "Δx·Δp ≥ h/(4π)",
    "description": "It is impossible to simultaneously know the exact position and momentum of an electron.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 322,
    "name": "Aufbau Principle",
    "formula": "Electrons fill orbitals from lowest to highest energy",
    "description": "Electrons are added to atomic orbitals starting with the lowest energy level.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 323,
    "name": "Hund's Rule",
    "formula": "Electrons fill degenerate orbitals singly before pairing",
    "description": "When filling orbitals of equal energy, electrons occupy separate orbitals with parallel spins before pairing.",
    "category": "Rule",
    "subject": "Chemistry"
  },
  {
    "id": 324,
    "name": "Pauli Exclusion Principle (Chemistry)",
    "formula": "No two electrons can have the same set of four quantum numbers",
    "description": "Each electron in an atom must have a unique set of quantum numbers.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 325,
    "name": "Bohr Model Energy Levels",
    "formula": "E_n = -13.6/n² eV",
    "description": "The energy of an electron in the nth energy level of a hydrogen atom.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 326,
    "name": "Ideal Gas Constant",
    "formula": "R = 0.0821 L·atm/(mol·K) = 8.314 J/(mol·K)",
    "description": "The proportionality constant in the ideal gas law, relating pressure, volume, temperature, and moles.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 327,
    "name": "Van der Waals Equation",
    "formula": "(P + a(n/V)²)(V - nb) = nRT",
    "description": "Modified ideal gas law accounting for molecular size and intermolecular forces.",
    "category": "Equation",
    "subject": "Chemistry"
  },
  {
    "id": 328,
    "name": "Dalton's Law",
    "formula": "P_total = P₁ + P₂ + P₃ + ...",
    "description": "The total pressure of a gas mixture equals the sum of partial pressures of individual gases.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 329,
    "name": "Gay-Lussac's Law",
    "formula": "P/T = constant (at constant V)",
    "description": "The pressure of a gas is directly proportional to its absolute temperature at constant volume.",
    "category": "Law",
    "subject": "Chemistry"
  },
  {
    "id": 330,
    "name": "Avogadro's Number",
    "formula": "N_A = 6.022 × 10²³ particles/mol",
    "description": "The number of atoms, molecules, or ions in one mole of a substance.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 331,
    "name": "Molar Mass",
    "formula": "M = m/n",
    "description": "The mass of one mole of a substance, equal to mass divided by number of moles.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 332,
    "name": "Density",
    "formula": "ρ = m/V",
    "description": "The mass per unit volume of a substance.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 333,
    "name": "Concentration (Molarity)",
    "formula": "M = n/V",
    "description": "The number of moles of solute per liter of solution.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 334,
    "name": "Dilution Formula",
    "formula": "M₁V₁ = M₂V₂",
    "description": "The relationship between concentrations and volumes before and after dilution.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 335,
    "name": "Mass Percent",
    "formula": "% = (mass solute / mass solution) × 100",
    "description": "The percentage by mass of solute in a solution.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 336,
    "name": "Parts Per Million",
    "formula": "ppm = (mass solute / mass solution) × 10⁶",
    "description": "The concentration expressed as parts per million.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 337,
    "name": "Colligative Properties - Boiling Point Elevation",
    "formula": "ΔT_b = K_b × m",
    "description": "The increase in boiling point is proportional to molality of solute particles.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 338,
    "name": "Colligative Properties - Freezing Point Depression",
    "formula": "ΔT_f = K_f × m",
    "description": "The decrease in freezing point is proportional to molality of solute particles.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 339,
    "name": "Osmotic Pressure",
    "formula": "π = MRT",
    "description": "The pressure required to prevent osmosis, proportional to molarity and temperature.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 340,
    "name": "Van't Hoff Factor",
    "formula": "i = actual particles / formula units",
    "description": "The number of particles a compound dissociates into in solution.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 341,
    "name": "Reaction Rate",
    "formula": "Rate = -Δ[A]/Δt = Δ[P]/Δt",
    "description": "The change in concentration of reactants or products per unit time.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 342,
    "name": "Rate Constant",
    "formula": "k = rate / [A]^m[B]^n",
    "description": "The proportionality constant in the rate law, temperature-dependent.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 343,
    "name": "Reaction Order",
    "formula": "Overall order = m + n",
    "description": "The sum of exponents in the rate law, determining how concentration affects rate.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 344,
    "name": "Half-Life (First Order)",
    "formula": "t₁/₂ = ln(2)/k = 0.693/k",
    "description": "The time required for half of reactant to be consumed in a first-order reaction.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 345,
    "name": "Half-Life (Second Order)",
    "formula": "t₁/₂ = 1/(k[A]₀)",
    "description": "The time required for half of reactant to be consumed in a second-order reaction.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 346,
    "name": "Activation Energy",
    "formula": "E_a = energy barrier for reaction",
    "description": "The minimum energy required for reactants to form products.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 347,
    "name": "Catalyst Effect",
    "formula": "Lowers activation energy, increases rate",
    "description": "Catalysts speed up reactions by providing alternative pathway with lower activation energy.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 348,
    "name": "Reaction Quotient",
    "formula": "Q = [C]^c[D]^d / [A]^a[B]^b",
    "description": "The ratio of product to reactant concentrations at any point in reaction.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 349,
    "name": "Equilibrium Constant from ΔG",
    "formula": "K = e^(-ΔG°/RT)",
    "description": "The relationship between standard free energy change and equilibrium constant.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 350,
    "name": "Reaction Direction Prediction",
    "formula": "If Q < K, forward; Q > K, reverse; Q = K, equilibrium",
    "description": "Comparison of reaction quotient to equilibrium constant predicts reaction direction.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 351,
    "name": "Common Ion Effect",
    "formula": "Adding common ion decreases solubility",
    "description": "The solubility of a salt decreases when a common ion is added to the solution.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 352,
    "name": "Solubility Product Constant",
    "formula": "K_sp = [A⁺]^m[B⁻]^n",
    "description": "The equilibrium constant for dissolution of a sparingly soluble salt.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 353,
    "name": "Ion Product",
    "formula": "IP = [A⁺]^m[B⁻]^n",
    "description": "The product of ion concentrations raised to their stoichiometric coefficients.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 354,
    "name": "Precipitation Prediction",
    "formula": "If IP > K_sp, precipitate forms",
    "description": "Comparison of ion product to solubility product predicts precipitation.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 355,
    "name": "Bronsted-Lowry Acid",
    "formula": "HA → H⁺ + A⁻",
    "description": "A substance that donates protons (H⁺ ions) in aqueous solution.",
    "category": "Definition",
    "subject": "Chemistry"
  },
  {
    "id": 356,
    "name": "Bronsted-Lowry Base",
    "formula": "B + H⁺ → BH⁺",
    "description": "A substance that accepts protons (H⁺ ions) in aqueous solution.",
    "category": "Definition",
    "subject": "Chemistry"
  },
  {
    "id": 357,
    "name": "Conjugate Acid-Base Pair",
    "formula": "HA/A⁻ or BH⁺/B",
    "description": "Two species differing by one proton; when acid loses H⁺, it becomes conjugate base.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 358,
    "name": "Autoionization of Water",
    "formula": "H₂O ⇌ H⁺ + OH⁻",
    "description": "Water molecules can act as both acid and base, producing hydronium and hydroxide ions.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 359,
    "name": "pKa",
    "formula": "pKa = -log(Ka)",
    "description": "The negative logarithm of acid dissociation constant, indicating acid strength.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 360,
    "name": "pKb",
    "formula": "pKb = -log(Kb)",
    "description": "The negative logarithm of base dissociation constant, indicating base strength.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 361,
    "name": "Relationship Between Ka and Kb",
    "formula": "Ka × Kb = Kw",
    "description": "For a conjugate acid-base pair, the product of Ka and Kb equals Kw.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 362,
    "name": "Buffer Capacity",
    "formula": "Maximum resistance to pH change",
    "description": "The ability of a buffer to resist pH changes, greatest when pH = pKa.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 363,
    "name": "Buffer Range",
    "formula": "pH = pKa ± 1",
    "description": "The effective pH range of a buffer, typically within one pH unit of pKa.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 364,
    "name": "Titration Equivalence Point",
    "formula": "Moles acid = Moles base",
    "description": "The point in titration where stoichiometrically equivalent amounts of acid and base have reacted.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 365,
    "name": "Titration End Point",
    "formula": "Indicator color change",
    "description": "The point where indicator changes color, ideally matching equivalence point.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 366,
    "name": "Redox Reaction",
    "formula": "Oxidation + Reduction",
    "description": "A reaction involving transfer of electrons from one species to another.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 367,
    "name": "Oxidation Number Rules",
    "formula": "Sum of oxidation numbers = charge",
    "description": "Rules for assigning oxidation numbers: elements = 0, monatomic ions = charge, etc.",
    "category": "Rule",
    "subject": "Chemistry"
  },
  {
    "id": 368,
    "name": "Balancing Redox Reactions",
    "formula": "Balance atoms, then electrons",
    "description": "Method for balancing redox reactions using half-reactions and electron transfer.",
    "category": "Method",
    "subject": "Chemistry"
  },
  {
    "id": 369,
    "name": "Standard Reduction Potential",
    "formula": "E° = tendency to gain electrons",
    "description": "The tendency of a species to gain electrons under standard conditions.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 370,
    "name": "Cell Potential",
    "formula": "E°_cell = E°_cathode - E°_anode",
    "description": "The potential difference between cathode and anode in an electrochemical cell.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 371,
    "name": "Spontaneity from E°",
    "formula": "If E°_cell > 0, reaction is spontaneous",
    "description": "A positive cell potential indicates a spontaneous redox reaction.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 372,
    "name": "Free Energy from Cell Potential",
    "formula": "ΔG° = -nFE°",
    "description": "The relationship between standard free energy change and standard cell potential.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 373,
    "name": "Faraday Constant",
    "formula": "F = 96,485 C/mol",
    "description": "The charge of one mole of electrons, used in electrochemical calculations.",
    "category": "Constant",
    "subject": "Chemistry"
  },
  {
    "id": 374,
    "name": "Electrolysis - Moles from Charge",
    "formula": "n = Q/(n_e × F)",
    "description": "The number of moles produced in electrolysis from charge passed and electrons per mole.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 375,
    "name": "Bond Energy",
    "formula": "Energy to break one mole of bonds",
    "description": "The energy required to break a chemical bond, typically in kJ/mol.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 376,
    "name": "Bond Length",
    "formula": "Distance between bonded nuclei",
    "description": "The average distance between nuclei of two bonded atoms.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 377,
    "name": "Bond Order",
    "formula": "Number of electron pairs between atoms",
    "description": "The number of chemical bonds between two atoms: single = 1, double = 2, triple = 3.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 378,
    "name": "Hybridization",
    "formula": "sp, sp², sp³, sp³d, sp³d²",
    "description": "The mixing of atomic orbitals to form hybrid orbitals for bonding.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 379,
    "name": "VSEPR Theory",
    "formula": "Electron pairs repel, minimize repulsion",
    "description": "Valence shell electron pair repulsion theory predicts molecular geometry.",
    "category": "Theory",
    "subject": "Chemistry"
  },
  {
    "id": 380,
    "name": "Molecular Geometry",
    "formula": "Based on number of electron domains",
    "description": "The three-dimensional arrangement of atoms in a molecule, predicted by VSEPR theory.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 381,
    "name": "Dipole Moment",
    "formula": "μ = q × d",
    "description": "The measure of molecular polarity, product of charge and distance.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 382,
    "name": "Intermolecular Forces",
    "formula": "London, dipole-dipole, hydrogen bonding",
    "description": "Forces between molecules: dispersion forces, dipole interactions, and hydrogen bonds.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 383,
    "name": "Hydrogen Bonding",
    "formula": "H bonded to N, O, or F",
    "description": "Strong dipole-dipole interaction when hydrogen is bonded to highly electronegative atoms.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 384,
    "name": "London Dispersion Forces",
    "formula": "Temporary dipoles from electron movement",
    "description": "Weak intermolecular forces from temporary charge separation due to electron motion.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 385,
    "name": "Crystal Lattice Energy",
    "formula": "Energy to separate ions to infinity",
    "description": "The energy required to completely separate one mole of solid ionic compound into gaseous ions.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 386,
    "name": "Born-Haber Cycle",
    "formula": "Sum of energy changes = lattice energy",
    "description": "A thermodynamic cycle relating lattice energy to other energy changes in ionic compound formation.",
    "category": "Method",
    "subject": "Chemistry"
  },
  {
    "id": 387,
    "name": "Coordination Number",
    "formula": "Number of ligands bonded to central atom",
    "description": "The number of atoms, ions, or molecules bonded to the central atom in a complex.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 388,
    "name": "Crystal Field Theory",
    "formula": "Ligands split d-orbital energies",
    "description": "Theory explaining color and magnetic properties of transition metal complexes.",
    "category": "Theory",
    "subject": "Chemistry"
  },
  {
    "id": 389,
    "name": "Spectrochemical Series",
    "formula": "I⁻ < Br⁻ < Cl⁻ < F⁻ < OH⁻ < ... < CN⁻",
    "description": "Ordering of ligands by their ability to split d-orbital energy levels.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 390,
    "name": "Isomerism",
    "formula": "Same formula, different structure",
    "description": "Compounds with same molecular formula but different arrangements of atoms.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 391,
    "name": "Stereoisomers",
    "formula": "Same connectivity, different spatial arrangement",
    "description": "Isomers with same atom connectivity but different three-dimensional orientations.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 392,
    "name": "Enantiomers",
    "formula": "Mirror image stereoisomers",
    "description": "Stereoisomers that are non-superimposable mirror images of each other.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 393,
    "name": "Diastereomers",
    "formula": "Non-mirror image stereoisomers",
    "description": "Stereoisomers that are not mirror images of each other.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 394,
    "name": "Optical Activity",
    "formula": "Ability to rotate plane-polarized light",
    "description": "The property of chiral molecules to rotate the plane of polarized light.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 395,
    "name": "Specific Rotation",
    "formula": "[α] = α/(l × c)",
    "description": "The rotation of plane-polarized light per unit path length and concentration.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 396,
    "name": "R/S Nomenclature",
    "formula": "Priority rules for chiral centers",
    "description": "System for naming enantiomers based on spatial arrangement of substituents.",
    "category": "Rule",
    "subject": "Chemistry"
  },
  {
    "id": 397,
    "name": "E/Z Nomenclature",
    "formula": "Priority rules for double bonds",
    "description": "System for naming geometric isomers around double bonds.",
    "category": "Rule",
    "subject": "Chemistry"
  },
  {
    "id": 398,
    "name": "Nucleophilic Substitution",
    "formula": "Nu⁻ + R-X → R-Nu + X⁻",
    "description": "Reaction where nucleophile replaces leaving group in organic molecule.",
    "category": "Reaction",
    "subject": "Chemistry"
  },
  {
    "id": 399,
    "name": "SN1 Mechanism",
    "formula": "Unimolecular, two-step, carbocation intermediate",
    "description": "Substitution mechanism involving rate-determining formation of carbocation.",
    "category": "Mechanism",
    "subject": "Chemistry"
  },
  {
    "id": 400,
    "name": "SN2 Mechanism",
    "formula": "Bimolecular, one-step, inversion of configuration",
    "description": "Substitution mechanism involving simultaneous bond breaking and formation.",
    "category": "Mechanism",
    "subject": "Chemistry"
  },
  {
    "id": 401,
    "name": "Elimination Reaction",
    "formula": "E1 or E2 mechanism",
    "description": "Reaction removing atoms or groups to form double or triple bonds.",
    "category": "Reaction",
    "subject": "Chemistry"
  },
  {
    "id": 402,
    "name": "Markovnikov's Rule",
    "formula": "H adds to carbon with more H's",
    "description": "In addition to alkenes, hydrogen adds to carbon with more hydrogens.",
    "category": "Rule",
    "subject": "Chemistry"
  },
  {
    "id": 403,
    "name": "Zaitsev's Rule",
    "formula": "Most substituted alkene is major product",
    "description": "In elimination reactions, the most stable (most substituted) alkene is favored.",
    "category": "Rule",
    "subject": "Chemistry"
  },
  {
    "id": 404,
    "name": "Aromaticity",
    "formula": "4n + 2 π electrons, planar, cyclic",
    "description": "Special stability of cyclic conjugated systems meeting Hückel's rule.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 405,
    "name": "Hückel's Rule",
    "formula": "4n + 2 π electrons for aromaticity",
    "description": "Aromatic compounds have 4n+2 delocalized π electrons in a planar ring.",
    "category": "Rule",
    "subject": "Chemistry"
  },
  {
    "id": 406,
    "name": "Electrophilic Aromatic Substitution",
    "formula": "E⁺ + Ar-H → Ar-E + H⁺",
    "description": "Reaction where electrophile replaces hydrogen on aromatic ring.",
    "category": "Reaction",
    "subject": "Chemistry"
  },
  {
    "id": 407,
    "name": "Directing Effects",
    "formula": "Ortho/para vs meta directors",
    "description": "Substituents on benzene ring direct incoming groups to specific positions.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 408,
    "name": "Aldol Condensation",
    "formula": "Carbonyl + enolate → β-hydroxy carbonyl",
    "description": "Reaction between carbonyl compounds forming carbon-carbon bonds.",
    "category": "Reaction",
    "subject": "Chemistry"
  },
  {
    "id": 409,
    "name": "Grignard Reaction",
    "formula": "R-Mg-X + C=O → R-C-OH",
    "description": "Reaction of Grignard reagents with carbonyl compounds to form alcohols.",
    "category": "Reaction",
    "subject": "Chemistry"
  },
  {
    "id": 410,
    "name": "Diels-Alder Reaction",
    "formula": "Diene + Dienophile → Cyclohexene",
    "description": "Cycloaddition reaction between conjugated diene and alkene to form six-membered ring.",
    "category": "Reaction",
    "subject": "Chemistry"
  },
  {
    "id": 411,
    "name": "Wittig Reaction",
    "formula": "Carbonyl + Phosphorus ylide → Alkene",
    "description": "Reaction converting carbonyl groups to alkenes using phosphorus ylides.",
    "category": "Reaction",
    "subject": "Chemistry"
  },
  {
    "id": 412,
    "name": "Retrosynthetic Analysis",
    "formula": "Working backwards from target molecule",
    "description": "Strategy for planning organic synthesis by breaking bonds in target molecule.",
    "category": "Method",
    "subject": "Chemistry"
  },
  {
    "id": 413,
    "name": "Protecting Groups",
    "formula": "Temporarily block reactive functional groups",
    "description": "Groups used to protect reactive sites during multi-step synthesis.",
    "category": "Concept",
    "subject": "Chemistry"
  },
  {
    "id": 414,
    "name": "Green Chemistry Principles",
    "formula": "12 principles for sustainable chemistry",
    "description": "Guidelines for designing chemical processes that minimize environmental impact.",
    "category": "Principle",
    "subject": "Chemistry"
  },
  {
    "id": 415,
    "name": "Atom Economy",
    "formula": "% = (MW of desired product / MW of all reactants) × 100",
    "description": "The percentage of reactant atoms incorporated into the final product.",
    "category": "Formula",
    "subject": "Chemistry"
  },
  {
    "id": 416,
    "name": "E-Factor",
    "formula": "E = mass waste / mass product",
    "description": "Environmental factor measuring waste generated per unit of product.",
    "category": "Formula",
    "subject": "Chemistry"
  }
];
