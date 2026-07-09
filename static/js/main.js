document.addEventListener('DOMContentLoaded', () => {
  const assessmentForm = document.getElementById('assessment-form');
  const steps = Array.from(document.querySelectorAll('.assessment-step'));
  const progressBar = document.getElementById('assessment-progress');
  const stepLabel = document.getElementById('step-label');
  const prevButton = document.getElementById('prev-step');
  const nextButton = document.getElementById('next-step');
  const submitButton = document.getElementById('submit-step');
  let currentStepIndex = 0;

  function updateStepDisplay() {
    steps.forEach((step, index) => {
      step.classList.toggle('active', index === currentStepIndex);
    });

    const percent = ((currentStepIndex + 1) / steps.length) * 100;
    if (progressBar) {
      progressBar.style.width = `${percent}%`;
    }
    if (stepLabel) {
      stepLabel.textContent = `Step ${currentStepIndex + 1} of ${steps.length}`;
    }

    if (prevButton) {
      prevButton.disabled = currentStepIndex === 0;
    }
    if (nextButton) {
      nextButton.classList.toggle('d-none', currentStepIndex === steps.length - 1);
    }
    if (submitButton) {
      submitButton.classList.toggle('d-none', currentStepIndex !== steps.length - 1);
    }
  }

  function validateCurrentStep() {
    const currentStep = steps[currentStepIndex];
    const inputs = Array.from(currentStep.querySelectorAll('input, select'));
    for (const input of inputs) {
      if (input.hasAttribute('required') && !input.checkValidity()) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        return false;
      }
      if (input.checkValidity()) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
      }
    }
    return true;
  }

  if (assessmentForm && steps.length > 0) {
    updateStepDisplay();

    nextButton?.addEventListener('click', () => {
      if (!validateCurrentStep()) {
        return;
      }
      if (currentStepIndex < steps.length - 1) {
        currentStepIndex += 1;
        updateStepDisplay();
      }
    });

    prevButton?.addEventListener('click', () => {
      if (currentStepIndex > 0) {
        currentStepIndex -= 1;
        updateStepDisplay();
      }
    });

    assessmentForm.addEventListener('submit', (event) => {
      if (!validateCurrentStep()) {
        event.preventDefault();
        return;
      }
    });

    assessmentForm.addEventListener('input', (event) => {
      const input = event.target;
      if (input.checkValidity()) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
      } else {
        input.classList.remove('is-valid');
      }
    });
  }
});
