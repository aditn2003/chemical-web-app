import React, { useEffect, useState } from "react";

function DropdownMenu() {
  const [selectedChemical, setSelectedChemical] = useState("");
  const [compoundNames, setCompoundNames] = useState<string[]>([]);
  useEffect(() => {
    fetch("http://localhost:5000/api/compoundNames")
      .then((res) => res.json())
      .then((data) => {
        setCompoundNames(data);
      })
      .catch((err) => console.error("Error fetching compound names:", err));
  }, []);

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedChemical(event.target.value);
    console.log("Selected:", event.target.value);
  };

  return (
    <>
      <label>Select chemical: </label>
      <select value={selectedChemical} onChange={handleChange}>
        <option value="">-- Choose a chemical --</option>
        {compoundNames.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </>
  );
}

export default DropdownMenu;
