import React from 'react';
import PropTypes from 'prop-types';

export const TaxRegimeComparison = ({ oldRegime, newRegime, onDownload }) => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-4">Tax Regime Comparison</h2>
      <table className="table-auto w-full border-collapse border border-gray-300">
        <thead>
          <tr>
            <th className="border px-4 py-2">Category</th>
            <th className="border px-4 py-2">Old Regime</th>
            <th className="border px-4 py-2">New Regime</th>
          </tr>
        </thead>
        <tbody>
          {Object.keys(oldRegime).map((key) => (
            <tr key={key}>
              <td className="border px-4 py-2">{key}</td>
              <td className="border px-4 py-2">{oldRegime[key]}</td>
              <td className="border px-4 py-2">{newRegime[key]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        onClick={onDownload}
        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 mt-4"
      >
        Download PDF
      </button>
    </div>
  );
};

TaxRegimeComparison.propTypes = {
  oldRegime: PropTypes.object.isRequired,
  newRegime: PropTypes.object.isRequired,
  onDownload: PropTypes.func.isRequired,
};