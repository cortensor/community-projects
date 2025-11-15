import React from "react";

function InputBoxClean({
  size,
  formData,
  setFormData,
  field,
  maxLength = 20,
  hasButton = false,
  buttonName = null,
}) {
  function handleChange(e) {
    const { name, value } = e.target;
    if (value.length <= maxLength) {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  }

  return (
    <div
      className="flex flex-col gap-1 text-sm text-[#B0B0B0]"
      style={{ width: size }}
    >
      <div className="relative h-full">
        <input
          type="text"
          name={field}
          value={formData?.[field] || ""}
          onChange={handleChange}
          maxLength={maxLength}
          style={{ width: size }}
          className={`bg-transparent border border-[#666] rounded-md px-3 py-2 text-[#E0E0E0] placeholder-gray-500 focus:outline-none focus:border-[#888] transition ${
            hasButton ? "pr-20" : ""
          }`}
          placeholder=""
        />

        {hasButton && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 h-6 w-16 bg-[#E0E0E0] text-[#222] text-xs font-medium rounded-full px-3 flex items-center justify-center hover:bg-[#d5d5d5] transition"
          >
            {buttonName}
          </button>
        )}
      </div>
    </div>
  );
}

export default InputBoxClean;
