import React from "react";

function InputBox({
  label,
  size,
  formData,
  setFormData,
  field,
  maxLength = 20,
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
      <label className="font-medium">{label}</label>
      <div className="relative">
        <input
          type="text"
          name={field}
          value={formData?.[field] || ""}
          onChange={handleChange}
          maxLength={maxLength}
          style={{ width: size }}
          className="bg-transparent border border-[#666] rounded-md px-3 py-2 text-[#E0E0E0] placeholder-gray-500 focus:outline-none focus:border-[#888] transition"
          placeholder=""
        />
      </div>
      <div className="flex w-full justify-end">
        <span className="text-xs text-[#888]">
          {formData?.[field]?.length || 0}/{maxLength}
        </span>
      </div>
    </div>
  );
}

export default InputBox;
