import React, { useState } from 'react';
import { DocumentUploadStep } from '../components/input/steps/DocumentUploadStep';
import { OCRReviewStep } from '../components/input/steps/OCRReviewStep';

export const InputPage = () => {
  const [step, setStep] = useState(1);
  const [ocrData, setOcrData] = useState({});

  const handleNext = () => {
    setStep((prevStep) => prevStep + 1);
  };

  const handleFileUpload = (file) => {
    // Call backend API to process the file and get OCR data
    // Simulating API call here
    const mockOcrData = { 'Income': '', 'Tax Paid': '', 'Deductions': '' };
    setOcrData(mockOcrData);
  };

  const handleUpdateOcrData = (updatedData) => {
    setOcrData(updatedData);
  };

  return (
    <div className="container mx-auto p-4">
      {step === 1 && (
        <DocumentUploadStep onNext={handleNext} onFileUpload={handleFileUpload} />
      )}
      {step === 2 && (
        <OCRReviewStep
          ocrData={ocrData}
          onUpdate={handleUpdateOcrData}
          onNext={handleNext}
        />
      )}
    </div>
  );
};