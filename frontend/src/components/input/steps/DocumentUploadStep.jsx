import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { ErrorBanner } from '../../common/ErrorBanner';

export const DocumentUploadStep = ({ onNext, onFileUpload }) => {
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);

  const handleFileChange = (event) => {
    const uploadedFile = event.target.files[0];
    if (!uploadedFile || !uploadedFile.name.match(/\.pdf$/)) {
      setError('Only PDF files are allowed.');
      return;
    }
    setError(null);
    setFile(uploadedFile);
    onFileUpload(uploadedFile);
  };

  const handleNext = () => {
    if (!file) {
      setError('Please upload a file before proceeding.');
      return;
    }
    onNext();
  };

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4">Upload Tax Documents</h2>
      {error && <ErrorBanner message={error} />}
      <input
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        className="mb-4"
      />
      <button
        onClick={handleNext}
        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
      >
        Next
      </button>
    </div>
  );
};

DocumentUploadStep.propTypes = {
  onNext: PropTypes.func.isRequired,
  onFileUpload: PropTypes.func.isRequired,
};