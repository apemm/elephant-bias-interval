import PaperD.Modes.AnalyticCharacteristic

/-!
# Conditional Fourier interface

The explicit characteristic-function inputs used by the curvature and shape
arguments.
-/

namespace Kagey131.PaperD.Modes

open Set Filter MeasureTheory
open scoped Topology ENNReal NNReal

/-- Explicit published-law inputs. The function `φ` belongs to the conditional
law; only its real part represents the fair-start density `g`. -/
structure ConditionalFourierHyp (a : ℝ) (g : ℝ → ℝ) (φ : ℝ → ℂ) : Prop where
  continuous : Continuous φ
  unit_bound : ∀ t, ‖φ t‖ ≤ 1
  norm_even : ∀ t, ‖φ (-t)‖ = ‖φ t‖
  decay : Tendsto (fun t => ‖φ t‖) atTop (𝓝 0)
  smoothing : ∀ t, 0 ≤ t → ‖φ t‖ ≤ ∫ v in Ioo (0 : ℝ) 1,
    ‖φ (t*v^a)‖ * ‖φ (t*(1-v)^a)‖
  fair_representation : g = normalizedFourierDensity (fun t => ((φ t).re : ℂ))

/-- Standard characteristic-function facts need not be supplied separately
when the conditional law is given as a probability measure with density. -/
theorem conditionalFourierHyp_of_probability_measure {a : ℝ} {g : ℝ → ℝ}
    {μ : Measure ℝ} [IsProbabilityMeasure μ] {ρ : ℝ → ℝ≥0}
    (hρ : Measurable ρ) (hμ : μ = volume.withDensity (fun x => (ρ x : ℝ≥0∞)))
    (hfp : ∀ t, 0 ≤ t → ‖charFun μ t‖ ≤ ∫ v in Ioo (0 : ℝ) 1,
      ‖charFun μ (t*v^a)‖ * ‖charFun μ (t*(1-v)^a)‖)
    (hrep : g = normalizedFourierDensity (fun t => ((charFun μ t).re : ℂ))) :
    ConditionalFourierHyp a g (charFun μ) := by
  refine ⟨continuous_charFun, (fun t => norm_charFun_le_one t), ?_,
    charFun_norm_tendsto_zero_of_density hρ hμ, hfp, hrep⟩
  intro t
  simp only [charFun_neg, RCLike.norm_conj]

end Kagey131.PaperD.Modes
