import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { ErrorBanner } from '../../common/ErrorBanner';

export const OCRReviewStep = ({ ocrData, onUpdate, onNext }) => {
  const [error, setError] = useState(null);

  const handleInputChange = (field, value) => {
    onUpdate({ ...ocrData, [field]: value });
  };

  const handleNext = () => {
    if (!ocrData || Object.values(ocrData).some((value) => !value)) {
      setError('Please complete all fields before proceeding.');
      return;
    }
    setError(null);
    onNext();
  };

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4">Review and Correct OCR Data</h2>
      {error && <ErrorBanner message={error} />}
      <form className="space-y-4">
        {Object.keys(ocrData).map((field) => (
          <div key={field} className="flex flex-col">
            <label htmlFor={field} className="font-medium">
              {field}
            </label>
            <input
              id={field}
              type="text"
              value={ocrData[field]}
              onChange={(e) => handleInputChange(field, e.target.value)}
              className="border p-2 rounded"
            />
          </div>
        ))}
      </form>
      <button
        onClick={handleNext}
        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 mt-4"
      >
        Next
      </button>
    </div>
  );
};

OCRReviewStep.propTypes = {
  ocrData: PropTypes.object.isRequired,
  onUpdate: PropTypes.func.isRequired,
  onNext: PropTypes.func.isRequired,
};