"use client";

import React, { useState, useCallback, useEffect, useId } from "react";
import * as XLSX from "xlsx";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import {
	PlusCircle,
	Trash2,
	UploadCloud,
	FileCog,
	Download,
	AlertCircle,
	CheckCircle,
	Info,
	Eye,
} from "lucide-react";

interface HeaderField {
	id: string;
	tagName: string;
	tagValue: string;
}

const escapeXml = (unsafe: string): string => {
	return unsafe.replace(/[<>&'"]/g, (c) => {
		switch (c) {
			case "<":
				return "&lt;";
			case ">":
				return "&gt;";
			case "&":
				return "&amp;";
			case "'":
				return "&apos;";
			case '"':
				return "&quot;";
			default:
				return c;
		}
	});
};

function sanitizeXmlTagName(name: string): string {
	// Replace spaces with underscores
	let tag = name.replace(/\s+/g, "_");
	// Remove invalid characters (allow only letters, digits, underscore, hyphen, period)
	tag = tag.replace(/[^a-zA-Z0-9_.-]/g, "");
	// Ensure tag starts with a letter or underscore
	if (!/^[a-zA-Z_]/.test(tag)) {
		tag = "_" + tag;
	}
	// If tag is empty after sanitization, use a fallback
	if (!tag) {
		tag = "EMPTY_TAG";
	}
	return tag;
}

export function ExcelToXmlConverter() {
	const [headerFields, setHeaderFields] = useState<HeaderField[]>([]);
	const [currentTagName, setCurrentTagName] = useState<string>("");
	const [currentTagValue, setCurrentTagValue] = useState<string>("");
	const [currentTagNameError, setCurrentTagNameError] = useState<
		string | undefined
	>(undefined);
	const [currentTagValueError, setCurrentTagValueError] = useState<
		string | undefined
	>(undefined);

	const [excelFile, setExcelFile] = useState<File | null>(null);
	const [originalFileName, setOriginalFileName] = useState<string>("");
	const [conversionProgress, setConversionProgress] = useState<number>(0);
	const [conversionStatus, setConversionStatus] = useState<
		"idle" | "validating" | "converting" | "completed" | "error"
	>("idle");
	const [xmlOutput, setXmlOutput] = useState<string | null>(null);
	const [statusMessage, setStatusMessage] = useState<string | null>(null);
	const { toast } = useToast();
	const formId = useId();

	const resetConverter = useCallback(() => {
		setHeaderFields([]);
		setCurrentTagName("");
		setCurrentTagValue("");
		setCurrentTagNameError(undefined);
		setCurrentTagValueError(undefined);
		setExcelFile(null);
		setOriginalFileName("");
		setConversionProgress(0);
		setConversionStatus("idle");
		setXmlOutput(null);
		setStatusMessage(null);
		const fileInput = document.getElementById(
			`${formId}-file-upload`
		) as HTMLInputElement;
		if (fileInput) {
			fileInput.value = "";
		}
	}, [formId]);

	const validateTagName = (name: string): string | undefined => {
		if (!name.trim()) return "Tag name cannot be empty.";
		if (!/^[a-zA-Z_][\w.-]*$/.test(name))
			return "Invalid XML tag name format. Use letters, numbers, underscore, period, or hyphen. Must start with a letter or underscore.";
		return undefined;
	};

	const validateTagValue = (value: string): string | undefined => {
		// Allowing empty tag values
		return undefined;
	};

	const handleCurrentTagNameChange = (value: string) => {
		setCurrentTagName(value);
		if (value.trim()) {
			// Only validate if not empty, error for empty is handled on add
			setCurrentTagNameError(validateTagName(value));
		} else {
			setCurrentTagNameError(undefined); // Clear error if user clears input
		}
	};

	const handleCurrentTagValueChange = (value: string) => {
		setCurrentTagValue(value);
		setCurrentTagValueError(validateTagValue(value)); // Validate immediately, empty is allowed
	};

	const handleAddNewHeaderField = () => {
		const tagNameError = validateTagName(currentTagName);
		// Tag value validation allows empty, so no error check here unless specific rules are added
		// const tagValueError = validateTagValue(currentTagValue);

		if (tagNameError) {
			setCurrentTagNameError(tagNameError);
			toast({
				title: "Validation Error",
				description: tagNameError,
				variant: "destructive",
			});
			return;
		}
		// Ensure currentTagNameError is cleared if it passes here (e.g. user corrected it)
		setCurrentTagNameError(undefined);
		// setCurrentTagValueError(tagValueError); // if tagValue had validation

		setHeaderFields([
			...headerFields,
			{
				id: Date.now().toString(),
				tagName: currentTagName.trim(), // Trim whitespace
				tagValue: currentTagValue, // Keep as is, might be intentionally spaced
			},
		]);
		setCurrentTagName("");
		setCurrentTagValue("");
		// Errors are already cleared or set by change handlers or above checks
	};

	const handleRemoveHeaderField = (idToRemove: string) => {
		const updatedFields = headerFields.filter(
			(field) => field.id !== idToRemove
		);
		setHeaderFields(updatedFields);
	};

	const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (file) {
			if (
				file.type ===
					"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
				file.type === "application/vnd.ms-excel"
			) {
				setExcelFile(file);
				setOriginalFileName(file.name);
				setStatusMessage(null);
			} else {
				setExcelFile(null);
				setOriginalFileName("");
				event.target.value = "";
				toast({
					title: "Invalid File Type",
					description: "Please upload a valid Excel file (.xlsx, .xls).",
					variant: "destructive",
				});
			}
		}
	};

	const validateAllInputsBeforeConversion = (): boolean => {
		if (!excelFile) {
			toast({
				title: "Missing File",
				description: "Please upload an Excel file.",
				variant: "destructive",
			});
			return false;
		}
		// Optionally, require at least one header field
		// if (headerFields.length === 0) {
		//   toast({
		//     title: "Missing Headers",
		//     description: "Please define at least one XML header field for the conversion.",
		//     variant: "destructive",
		//   });
		//   return false;
		// }
		return true;
	};

	const generateXmlContent = async (): Promise<string> => {
		let dataRowsXml = "";
		if (excelFile) {
			const arrayBuffer = await excelFile.arrayBuffer();
			const workbook = XLSX.read(arrayBuffer, { type: "array" });
			const sheetName = workbook.SheetNames[0];
			const worksheet = workbook.Sheets[sheetName];
			const jsonData: any[] = XLSX.utils.sheet_to_json(worksheet, {
				header: 1,
			});

			// Get headers from the first row
			const headers: string[] = jsonData[0] || [];

			// Loop through data rows (skip header row)
			for (let i = 1; i < jsonData.length; i++) {
				const row = jsonData[i];
				dataRowsXml += "    <ROW>\n";
				headers.forEach((header, idx) => {
					// Replace spaces with underscores in tag names
					const tag = escapeXml(String(header || `COLUMN${idx + 1}`)).replace(
						/ /g,
						"_"
					);
					const value = escapeXml(String(row[idx] ?? ""));
					dataRowsXml += `      <${tag}>${value}</${tag}>\n`;
				});
				dataRowsXml += "    </ROW>\n";
			}
		}

		const headerItemsXml = headerFields
			.filter(
				(field) => field.tagName.trim() && !validateTagName(field.tagName)
			)
			.map(
				(field) =>
					`    <${field.tagName}>${escapeXml(field.tagValue)}</${
						field.tagName
					}>`
			)
			.join("\n");

		const headerXmlBlock =
			headerFields.length > 0
				? `  <HEADER>\n${headerItemsXml}\n  </HEADER>`
				: `  <HEADER></HEADER>`;

		return `<?xml version="1.0" encoding="UTF-8"?>\n<ROOT>
${headerXmlBlock}
  <DATA>
${dataRowsXml}  </DATA>
</ROOT>`;
	};

	const handleConvert = async () => {
		setConversionStatus("validating");
		setStatusMessage(null);
		setXmlOutput(null);

		if (!validateAllInputsBeforeConversion()) {
			setConversionStatus("error");
			setStatusMessage("Please fix the errors in the form.");
			return;
		}

		setConversionStatus("converting");
		setStatusMessage("Conversion in progress...");
		setConversionProgress(0);

		const progressInterval = setInterval(() => {
			setConversionProgress((prev) => {
				if (prev >= 100) {
					clearInterval(progressInterval);
					return 100;
				}
				return prev + 10;
			});
		}, 200);

		setTimeout(async () => {
			clearInterval(progressInterval);
			setConversionProgress(100);
			try {
				const generatedXml = await generateXmlContent();
				setXmlOutput(generatedXml);
				setConversionStatus("completed");
				setStatusMessage(
					"Conversion successful! Your XML file is ready for download."
				);
			} catch (error) {
				setConversionStatus("error");
				setStatusMessage(
					error instanceof Error
						? error.message
						: "An unknown error occurred during conversion."
				);
				toast({
					title: "Conversion Error",
					description:
						error instanceof Error
							? error.message
							: "An unknown error occurred.",
					variant: "destructive",
				});
			}
		}, 2200);
	};

	const handleDownload = () => {
		if (!xmlOutput || !originalFileName) return;
		const blob = new Blob([xmlOutput], { type: "application/xml" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		const baseName =
			originalFileName.substring(0, originalFileName.lastIndexOf(".")) ||
			originalFileName;
		a.download = `${baseName}.xml`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
		toast({
			title: "Download Started",
			description: `${baseName}.xml is downloading.`,
		});
	};

	const getStatusAlertVariant = (): "default" | "destructive" | undefined => {
		if (conversionStatus === "error") return "destructive";
		if (conversionStatus === "completed") return "default";
		return "default";
	};

	const getStatusAlertIcon = () => {
		if (conversionStatus === "completed")
			return <CheckCircle className="h-4 w-4" />;
		if (conversionStatus === "error")
			return <AlertCircle className="h-4 w-4" />;
		if (conversionStatus === "converting" || conversionStatus === "validating")
			return <Info className="h-4 w-4" />;
		return null;
	};

	return (
		<Card className="w-full max-w-2xl mx-auto shadow-2xl">
			<CardHeader>
				<CardTitle className="text-3xl font-headline text-center text-primary">
					Excel2XML Converter
				</CardTitle>
				<CardDescription className="text-center">
					Define XML headers, upload an Excel file, and convert it to XML
					format.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-6">
				<div className="space-y-4 p-4 border rounded-md shadow-sm">
					<h3 className="text-lg font-semibold text-accent mb-4">
						1. Define XML Header
					</h3>

					<div className="space-y-3 p-3 border-b border-border pb-6">
						<div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
							<div>
								<Label htmlFor={`${formId}-current-tag-name`}>
									New Tag Name
								</Label>
								<Input
									id={`${formId}-current-tag-name`}
									placeholder="e.g., CALLREPORT_ID"
									value={currentTagName}
									onChange={(e) => handleCurrentTagNameChange(e.target.value)}
									className={
										currentTagNameError
											? "border-destructive ring-destructive"
											: ""
									}
									aria-invalid={!!currentTagNameError}
									aria-describedby={
										currentTagNameError
											? `${formId}-current-tag-name-error`
											: undefined
									}
								/>
								{currentTagNameError && (
									<p
										id={`${formId}-current-tag-name-error`}
										className="text-xs text-destructive mt-1"
									>
										{currentTagNameError}
									</p>
								)}
							</div>
							<div>
								<Label htmlFor={`${formId}-current-tag-value`}>
									New Tag Value
								</Label>
								<Input
									id={`${formId}-current-tag-value`}
									placeholder="e.g., DTR001"
									value={currentTagValue}
									onChange={(e) => handleCurrentTagValueChange(e.target.value)}
									className={
										currentTagValueError
											? "border-destructive ring-destructive"
											: ""
									} // This error state might not be used if values can be empty
									aria-invalid={!!currentTagValueError}
									aria-describedby={
										currentTagValueError
											? `${formId}-current-tag-value-error`
											: undefined
									}
								/>
								{/* currentTagValueError display can be omitted if empty values are always fine and no other validation rules */}
							</div>
						</div>
						<Button
							variant="outline"
							onClick={handleAddNewHeaderField}
							className="mt-3 border-primary text-primary hover:bg-primary/10 hover:text-primary w-full md:w-auto"
						>
							<PlusCircle className="mr-2 h-4 w-4" /> Add This Header Field
						</Button>
					</div>

					<div className="mt-4 p-4 border rounded-md bg-muted/20 shadow-inner">
						<div className="flex items-center mb-3">
							<Eye className="h-5 w-5 mr-2 text-accent" />
							<h4 className="text-md font-semibold text-accent">
								Configured Header Tags
							</h4>
						</div>
						{headerFields.length > 0 ? (
							<ul className="space-y-2">
								{headerFields.map((field) => (
									<li
										key={field.id}
										className="flex justify-between items-center p-2.5 bg-background rounded-md border border-input shadow-sm hover:shadow-md transition-shadow duration-150 ease-in-out"
									>
										<code className="text-sm text-foreground break-all mr-3 flex-grow select-all">
											{`<${escapeXml(field.tagName)}>${escapeXml(
												field.tagValue
											)}</${escapeXml(field.tagName)}>`}
										</code>
										<Button
											variant="ghost"
											size="icon"
											onClick={() => handleRemoveHeaderField(field.id)}
											className="text-destructive hover:bg-destructive/10 shrink-0"
											aria-label={`Remove header field ${field.tagName}`}
										>
											<Trash2 className="h-4 w-4" />
										</Button>
									</li>
								))}
							</ul>
						) : (
							<p className="text-sm text-muted-foreground italic text-center py-2">
								No header fields defined. Use the inputs above to add tags.
							</p>
						)}
					</div>
				</div>

				<Separator />

				<div className="space-y-2 p-4 border rounded-md shadow-sm">
					<h3 className="text-lg font-semibold text-accent">
						2. Upload Excel File
					</h3>
					<Label htmlFor={`${formId}-file-upload`}>
						Select .xlsx or .xls file
					</Label>
					<Input
						id={`${formId}-file-upload`}
						type="file"
						accept=".xlsx, .xls, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
						onChange={handleFileChange}
						className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
						aria-describedby={`${formId}-file-name`}
					/>
					<p
						id={`${formId}-file-name`}
						className="text-sm text-muted-foreground"
					>
						{originalFileName
							? `Selected file: ${originalFileName}`
							: "No file selected."}
					</p>
				</div>

				<Separator />

				<div className="space-y-4 p-4 border rounded-md shadow-sm">
					<h3 className="text-lg font-semibold text-accent">
						3. Convert & Download
					</h3>
					<Button
						onClick={handleConvert}
						disabled={
							conversionStatus === "converting" ||
							conversionStatus === "validating"
						}
						className="w-full bg-primary hover:bg-primary/90 text-primary-foreground text-lg py-6"
					>
						<FileCog className="mr-2 h-5 w-5" />
						{conversionStatus === "converting"
							? "Converting..."
							: "Convert to XML"}
					</Button>

					{(conversionStatus === "converting" ||
						conversionStatus === "completed" ||
						conversionStatus === "error" ||
						conversionStatus === "validating") && (
						<div className="space-y-2 mt-4">
							<Progress
								value={conversionProgress}
								className="w-full transition-all duration-300 ease-linear"
							/>
							{statusMessage && (
								<Alert
									variant={getStatusAlertVariant()}
									className="mt-2 transition-opacity duration-300"
								>
									{getStatusAlertIcon()}
									<AlertTitle>
										{conversionStatus === "completed"
											? "Success!"
											: conversionStatus === "error"
											? "Error!"
											: conversionStatus === "converting"
											? "Processing..."
											: conversionStatus === "validating"
											? "Validating..."
											: "Status"}
									</AlertTitle>
									<AlertDescription>{statusMessage}</AlertDescription>
								</Alert>
							)}
						</div>
					)}
				</div>

				{conversionStatus === "completed" && xmlOutput && (
					<div className="mt-6 flex flex-col sm:flex-row gap-4">
						<Button
							onClick={handleDownload}
							className="w-full sm:w-auto flex-1 bg-accent hover:bg-accent/90 text-accent-foreground text-lg py-6"
						>
							<Download className="mr-2 h-5 w-5" /> Download XML
						</Button>
						<Button
							onClick={resetConverter}
							variant="outline"
							className="w-full sm:w-auto flex-1 text-lg py-6 border-primary text-primary hover:bg-primary/10"
						>
							Convert Another File
						</Button>
					</div>
				)}
				{conversionStatus === "error" && (
					<Button
						onClick={resetConverter}
						variant="outline"
						className="w-full mt-4 text-lg py-6 border-primary text-primary hover:bg-primary/10"
					>
						Try Again
					</Button>
				)}
			</CardContent>
			<CardFooter className="flex justify-center">
				<p className="text-xs text-muted-foreground">
					Excel2XML Converter &copy; {new Date().getFullYear()}
				</p>
			</CardFooter>
		</Card>
	);
}
